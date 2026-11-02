"""Harness acceptance tests; no network, real SQLite and filesystem checkpoints."""
import asyncio
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from examples.harness_demo import DEMO_PAGES, DemoBrowser, DemoLLM
from harness.budget import BudgetLimits
from harness.context import Context
from harness.runtime import Runtime
from harness.tools import Parameter, ToolRegistry, ToolValidationError
from resumeagent.llm import client
from resumeagent.main import HomepageDesignAgent


class HarnessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        patcher = patch.object(client,'token_log_file',str(self.root/'tokens.json'))
        patcher.start(); self.addCleanup(patcher.stop)
        self.llm = DemoLLM()
        self.browser = DemoBrowser()
        self.agent = HomepageDesignAgent(save_file=str(self.root/'outputs'),model='demo-model',llm=self.llm,browser=self.browser)
        self.agent.gen_img = False

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration=5

    def runtime(self, **limits):
        return Runtime(self.agent,storage_root=self.root/'storage',limits=BudgetLimits(**limits))

    async def test_full_run_stage_sequence_concurrency_usage_and_trace(self):
        runtime = self.runtime(max_concurrency=2)
        run_id = runtime.create_run({'basic_information':'PRIVATE_USER_PROFILE'},feedback='PRIVATE_FEEDBACK')
        result = await runtime.execute(run_id)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(len(runtime.state.pages(run_id)),3)
        self.assertEqual(self.llm.peak,2)
        self.assertGreater(result['usage']['cost'],0)
        self.assertEqual(result['usage']['prompt_tokens'],len(self.llm.calls)*100)
        tasks = runtime.state.tasks(run_id)
        for page in runtime.state.pages(run_id):
            stages=[t['stage'] for t in tasks if t['page_id']==page['id']]
            self.assertEqual(stages,['generation','rendering','evaluation','refinement','rendering','evaluation','validation'])
            self.assertEqual(page['status'],'completed')
            self.assertTrue(all(Path(path).exists() for path in page['files'].values()))
        events=runtime.tracer.query(run_id)
        self.assertTrue({'llm.started','llm.usage','tool.started','task.completed','run.finished'} <= {e['event'] for e in events})
        raw=json.dumps(events)
        self.assertNotIn('PRIVATE_USER_PROFILE',raw)
        self.assertNotIn('PRIVATE_FEEDBACK',raw)
        self.assertNotIn('messages',raw)
        stored=(runtime.root/'runs'/run_id/'trace.jsonl').read_text(encoding='utf-8')
        self.assertEqual(len(stored.splitlines()),len(events))
        self.assertEqual(runtime.tracer.query(run_id,after_id=events[-2]['id']),events[-1:])

    async def test_partial_failure_resume_in_new_runtime_skips_completed_pages(self):
        self.llm.fail_page='projects.html'; self.llm.fail_times=1
        runtime=self.runtime(max_retries=0)
        run_id=runtime.create_run(pages=DEMO_PAGES)
        self.assertEqual((await runtime.execute(run_id))['status'],'failed')
        self.assertEqual([p['status'] for p in runtime.state.pages(run_id)],['completed','failed','completed'])
        before=Counter(self.llm.calls)
        recovered=self.runtime(max_retries=0)
        self.assertEqual((await recovered.resume(run_id))['status'],'completed')
        after=Counter(self.llm.calls)
        self.assertEqual(after[('generation','index.html')],before[('generation','index.html')])
        self.assertEqual(after[('generation','skills.html')],before[('generation','skills.html')])
        self.assertEqual(after[('generation','projects.html')],before[('generation','projects.html')]+1)
        errors=json.dumps(recovered.tracer.query(run_id))
        self.assertNotIn('sk-DO-NOT-LOG',errors)
        self.assertNotIn('private profile',errors)
        self.assertEqual(recovered.state.get_run(run_id)['id'],run_id)

    async def test_failed_render_resume_does_not_repeat_generation(self):
        original=self.browser.get_screenshot
        failures=[True]
        def render(html,output):
            if failures:
                failures.pop()
                raise RuntimeError('Render unavailable')
            return original(html,output)
        self.browser.get_screenshot=render
        runtime=self.runtime(max_retries=0)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        self.assertEqual((await runtime.execute(run_id))['status'],'failed')
        self.assertEqual(runtime.state.pages(run_id)[0]['stage'],'rendering')
        self.assertEqual((await runtime.resume(run_id))['status'],'completed')
        self.assertEqual(Counter(self.llm.calls)[('generation','index.html')],1)

    async def test_retry_is_finite_and_recorded(self):
        self.llm.fail_page='index.html';self.llm.fail_times=99
        runtime=self.runtime(max_retries=1)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        result=await runtime.execute(run_id)
        self.assertEqual(result['status'],'failed')
        task=next(t for t in runtime.state.tasks(run_id) if t['stage']=='generation')
        self.assertEqual((task['attempts'],task['retries']),(2,1))
        self.assertEqual(result['retries'],1)

    async def test_cost_budget_stops_followups_and_can_resume_with_larger_budget(self):
        runtime=self.runtime(max_cost=.0001,max_concurrency=1)
        run_id=runtime.create_run(pages=DEMO_PAGES)
        result=await runtime.execute(run_id)
        self.assertEqual(result['status'],'budget_exceeded')
        self.assertEqual(len(self.llm.calls),1)
        self.assertEqual(self.browser.calls,[])
        self.assertEqual(result['error'],'max_cost')
        runtime.set_limits(run_id,replace(runtime.budget.limits,max_cost=1))
        self.assertEqual((await runtime.resume(run_id))['status'],'completed')

    async def test_token_limit_and_zero_budget(self):
        runtime=self.runtime(max_prompt_tokens=100,max_concurrency=1)
        run_id=runtime.create_run(pages=DEMO_PAGES)
        self.assertEqual((await runtime.execute(run_id))['error'],'max_prompt_tokens')
        before=len(self.llm.calls)
        zero=self.runtime(max_cost=0)
        run_id=zero.create_run(pages=DEMO_PAGES)
        self.assertEqual((await zero.execute(run_id))['status'],'budget_exceeded')
        self.assertEqual(before,len(self.llm.calls))

    async def test_early_acceptance_and_iteration_cap(self):
        self.llm.needs_refinement=False
        runtime=self.runtime(max_iterations=4)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        self.assertEqual((await runtime.execute(run_id))['status'],'completed')
        self.assertFalse(any(s=='refinement' for s,_ in self.llm.calls))
        self.llm.needs_refinement=True
        capped=self.runtime(max_iterations=0)
        run_id=capped.create_run(pages=DEMO_PAGES[:1])
        self.assertEqual((await capped.execute(run_id))['status'],'completed')
        self.assertTrue(any(e['event']=='iteration.limit' for e in capped.tracer.query(run_id)))

    async def test_text_only_branch_skips_visual_evaluation(self):
        self.agent.vision=False
        runtime=self.runtime(max_iterations=1)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        self.assertEqual((await runtime.execute(run_id))['status'],'completed')
        self.assertFalse(any(stage=='evaluation' for stage,_ in self.llm.calls))
        self.assertEqual(Counter(self.llm.calls)[('refinement','index.html')],1)

    async def test_cancel_from_another_controller_persists_and_no_late_write(self):
        self.llm.delay=.2
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        operation=asyncio.create_task(runtime.execute(run_id))
        for _ in range(200):
            if self.llm.active:
                break
            await asyncio.sleep(.01)
        self.assertGreater(self.llm.active,0)
        controller=Runtime(storage_root=runtime.root)
        controller.cancel(run_id)
        result=await operation
        self.assertEqual(result['status'],'cancelled')
        await asyncio.sleep(.25) # A late provider response cannot save a page.
        self.assertEqual(self.browser.calls,[])
        self.assertFalse((Path(result['files']['output_dir'])/'index.html').exists())
        self.assertGreater(runtime.state.get_run(run_id)['usage']['prompt_tokens'],0)

    async def test_prestart_cancel_is_not_ignored(self):
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        runtime.cancel(run_id)
        self.assertEqual((await runtime.execute(run_id))['status'],'cancelled')
        self.assertEqual(self.llm.calls,[])

    async def test_request_timeout_and_late_usage(self):
        self.llm.delay=.15
        runtime=self.runtime(request_timeout=.02,max_retries=2)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        self.assertEqual((await runtime.execute(run_id))['status'],'timed_out')
        await asyncio.sleep(.2)
        self.assertEqual(len(self.llm.calls),1) # No retry storm after a timed-out paid call.
        self.assertEqual(runtime.state.get_run(run_id)['usage']['prompt_tokens'],100)
        self.assertEqual(self.browser.calls,[])

    async def test_run_walltime_budget_is_cumulative(self):
        self.llm.delay=.15
        runtime=self.runtime(max_run_seconds=.03)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        result=await runtime.execute(run_id)
        self.assertEqual(result['status'],'budget_exceeded')
        self.assertEqual(result['error'],'max_run_seconds')
        await asyncio.sleep(.2)
        self.assertEqual((await runtime.resume(run_id))['status'],'budget_exceeded')

    async def test_completed_artifact_tampering_regenerates_only_affected_page(self):
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES)
        await runtime.execute(run_id)
        pages=runtime.state.pages(run_id)
        Path(pages[1]['files']['html']).write_text('<html>changed</html>')
        before=Counter(self.llm.calls)
        self.assertEqual((await runtime.resume(run_id))['status'],'completed')
        after=Counter(self.llm.calls)
        self.assertEqual(after[('generation','index.html')],before[('generation','index.html')])
        self.assertEqual(after[('generation','projects.html')],before[('generation','projects.html')]+1)

    async def test_lease_excludes_second_executor_and_recovers_after_expiry(self):
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        runtime.state.claim(run_id,'other-owner')
        with self.assertRaises(RuntimeError):
            await runtime.execute(run_id)
        with runtime.state.db.connect() as conn:
            conn.execute('UPDATE runs SET lease_until=? WHERE id=?',(time.time()-1,run_id))
        self.assertEqual((await runtime.resume(run_id))['status'],'completed')

    async def test_tool_validation_and_output_confinement(self):
        tools=ToolRegistry()
        tools.register('double','Double an integer',{'value':Parameter(int)},lambda value:value*2)
        self.assertEqual((await tools.acall('double',value=2)).value,4)
        for arguments in ({},{'value':'2'},{'value':2,'extra':1}):
            with self.assertRaises(ToolValidationError):
                await tools.acall('double',**arguments)
        with self.assertRaises(ToolValidationError):
            self.agent.tools.call('filesystem.write_json',path=str(self.root/'escape.json'),data={})
        with self.assertRaises(ValueError):
            self.agent.validate_page_spec({'html_name':'../escape.html'})
        self.assertTrue(tools.describe()[0]['description'])

    async def test_context_is_bounded_and_copy_isolated(self):
        context=Context({'basic_information':'private'},feedback='feedback',plan=DEMO_PAGES)
        page={'spec':DEMO_PAGES[0],'files':{'screenshot':'one.png'},'checkpoint':{'history':[{'n':i} for i in range(10)]}}
        generated=context.build('generation',page)
        evaluated=context.build('evaluation',page)
        refined=context.build('refinement',page)
        self.assertNotIn('profile',evaluated)
        self.assertNotIn('website_plan',refined)
        self.assertEqual(len(refined['history']),2)
        generated['profile']['basic_information']='changed'
        self.assertEqual(context.profile['basic_information'],'private')

    async def test_two_runs_usage_is_attributed_separately(self):
        first=self.runtime(max_concurrency=1)
        second=self.runtime(max_concurrency=1)
        ids=[rt.create_run(pages=DEMO_PAGES[:1]) for rt in (first,second)]
        results=await asyncio.gather(first.execute(ids[0]),second.execute(ids[1]))
        for result in results:
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['usage']['prompt_tokens'],400)
        self.assertEqual(client.read_tokens()['demo-model'][0],800)

    async def test_gui_actions_are_managed_and_trace_tools(self):
        self.agent.runtime_options={'storage_root':str(self.root/'storage')}
        pages=await asyncio.to_thread(self.agent.managed_action,'plan')
        self.assertEqual(len(pages),3)
        run_id=self.agent.last_run_id
        inspector=self.runtime()
        self.assertEqual(inspector.state.get_run(run_id)['status'],'completed')
        self.assertEqual(len(inspector.state.pages(run_id)),3)
        await asyncio.to_thread(self.agent.managed_action,'write_original_website',pages[0])
        generated=self.agent.last_run_id
        self.assertTrue(any(e['event']=='tool.completed' and e.get('tool')=='browser.render' for e in inspector.tracer.query(generated)))
        self.assertEqual(inspector.state.pages(generated)[0]['status'],'completed')
        self.assertTrue(inspector.state.tasks(generated)[0]['files']['html'])

    async def test_missing_usage_fails_closed_when_cost_is_capped(self):
        async def no_usage(messages,**kwargs):
            return '```html\n<html></html>\n```'
        self.agent.llm.response_async=no_usage
        runtime=self.runtime(max_cost=1)
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        result=await runtime.execute(run_id)
        self.assertEqual(result['status'],'budget_exceeded')
        self.assertEqual(result['error'],'usage_unavailable')
        self.assertEqual(self.browser.calls,[])

    async def test_same_output_directory_cannot_be_owned_by_two_runs(self):
        runtime=self.runtime()
        directory=str(self.root/'shared-output')
        first=runtime.create_run(pages=DEMO_PAGES[:1],output_dir=directory)
        second=runtime.create_run(pages=DEMO_PAGES[:1],output_dir=directory)
        runtime.state.claim(first,'active')
        with self.assertRaises(RuntimeError):
            runtime.state.claim(second,'other')
        runtime.state.release(first,'active')
        runtime.state.claim(second,'other')
        runtime.state.release(second,'other')

    async def test_external_asyncio_cancellation_saves_state(self):
        self.llm.delay=.15
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        operation=asyncio.create_task(runtime.execute(run_id))
        while not self.llm.active:
            await asyncio.sleep(.01)
        operation.cancel()
        result=await operation
        self.assertEqual(result['status'],'cancelled')
        self.assertTrue(any(t['status']=='interrupted' for t in runtime.state.tasks(run_id)))
        await asyncio.sleep(.2)
        self.assertEqual(self.browser.calls,[])

    async def test_process_kill_checkpoint_survives_new_process(self):
        import subprocess
        import sys
        worker_code = """
import asyncio,json,sys
from pathlib import Path
from examples.harness_demo import DemoLLM,DemoBrowser,DEMO_PAGES
from harness.context import CURRENT_EXECUTION
from harness.runtime import Runtime
from harness.budget import BudgetLimits
from resumeagent.main import HomepageDesignAgent
from resumeagent.llm import client
root=Path(sys.argv[1]);client.token_log_file=str(root/'tokens.json')
class SlowPage(DemoLLM):
 async def response_async(self,messages,**kwargs):
  scope=CURRENT_EXECUTION.get()
  if scope.stage=='generation' and scope.runtime.state.page(scope.page_id)['spec']['html_name']=='projects.html':
   await asyncio.sleep(60)
  return await super().response_async(messages,**kwargs)
agent=HomepageDesignAgent(model='demo-model',save_file=str(root/'out'),llm=SlowPage(),browser=DemoBrowser());agent.gen_img=False
runtime=Runtime(agent,storage_root=root/'storage',limits=BudgetLimits(max_retries=0,max_concurrency=3))
run_id=runtime.create_run(pages=DEMO_PAGES)
(root/'worker-id.txt').write_text(run_id)
asyncio.run(runtime.execute(run_id))
"""
        process=subprocess.Popen([sys.executable,'-c',worker_code,str(self.root)],cwd=Path(__file__).resolve().parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            marker=self.root/'worker-id.txt'
            deadline=time.monotonic()+20
            while not marker.exists() and time.monotonic()<deadline:
                await asyncio.sleep(.05)
            self.assertTrue(marker.exists(),'Child worker did not initialize')
            runtime=self.runtime()
            run_id=marker.read_text()
            while time.monotonic()<deadline:
                pages=runtime.state.pages(run_id)
                if sum(p['status']=='completed' for p in pages)==2:
                    break
                await asyncio.sleep(.05)
            self.assertEqual(sum(p['status']=='completed' for p in pages),2)
            process.kill(); process.wait(timeout=5)
            # Simulate passage of the 30-second crash lease without slowing the suite.
            with runtime.state.db.connect() as conn:
                conn.execute('UPDATE runs SET lease_until=? WHERE id=?',(time.time()-1,run_id))
            result=await runtime.resume(run_id)
            self.assertEqual(result['status'],'completed')
            generations=[name for stage,name in self.llm.calls if stage=='generation']
            self.assertEqual(generations,['projects.html'])
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=5)

    async def test_cancelling_render_keeps_lease_until_worker_finishes(self):
        import threading
        started=threading.Event()
        original=self.browser.get_screenshot
        def slow_render(html,output):
            started.set()
            time.sleep(.3)
            return original(html,output)
        self.browser.get_screenshot=slow_render
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        operation=asyncio.create_task(runtime.execute(run_id))
        while not started.is_set():
            await asyncio.sleep(.01)
        runtime.cancel(run_id)
        self.assertEqual((await operation)['status'],'cancelled')
        other=self.runtime()
        with self.assertRaises(RuntimeError):
            await other.resume(run_id)
        await asyncio.sleep(.4)
        self.assertEqual((await other.resume(run_id))['status'],'completed')
        self.assertEqual(Counter(self.llm.calls)[('generation','index.html')],1)

    async def test_separate_css_full_runtime_flow(self):
        self.agent.css_frame=None
        runtime=self.runtime()
        run_id=runtime.create_run(pages=DEMO_PAGES[:1])
        result=await runtime.execute(run_id)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(Path(runtime.state.pages(run_id)[0]['files']['css']).is_file())


if __name__ == '__main__':
    unittest.main()
