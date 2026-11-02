"""Fault injection at external boundaries; recovery uses real persisted checkpoints."""
import asyncio
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from evals.support import Faults, load_cases, page_specs, runtime_factory
from harness.budget import BudgetLimits
from resumeagent.llm import client


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.case=load_cases()[0]
        patcher=patch.object(client,'token_log_file',str(self.root/'tokens.json'))
        patcher.start();self.addCleanup(patcher.stop)

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration=5

    async def test_api_failure_has_finite_retry_and_persisted_attempts(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_retries=1),faults=Faults(api_failures=1))
        try:
            run_id=runtime.create_run(self.case['profile'],pages=page_specs(self.case))
            self.assertEqual((await runtime.execute(run_id))['status'],'completed')
            self.assertTrue(any(t['retries']==1 and t['attempts']==2 for t in runtime.state.tasks(run_id)))
        finally:
            await runtime.aclose()

    async def test_page_generation_failure_resume_skips_other_pages(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_retries=0),faults=Faults(page_failures=1))
        try:
            run_id=runtime.create_run(self.case['profile'],pages=page_specs(self.case))
            self.assertEqual((await runtime.execute(run_id))['status'],'failed')
            completed=[p for p in runtime.state.pages(run_id) if p['status']=='completed']
            self.assertEqual(len(completed),2)
            before=dict(runtime.agent.llm.calls)
            self.assertEqual((await runtime.resume(run_id))['status'],'completed')
            for page in completed:
                key=('generation',page['spec']['html_name'])
                self.assertEqual(runtime.agent.llm.calls[key],before[key])
        finally:
            await runtime.aclose()

    async def test_browser_render_failure_restarts_at_rendering(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_retries=0),faults=Faults(render_failures=1))
        try:
            run_id=runtime.create_run(self.case['profile'],pages=page_specs(self.case))
            self.assertEqual((await runtime.execute(run_id))['status'],'failed')
            first=runtime.state.pages(run_id)[0]
            self.assertEqual(first['stage'],'rendering')
            self.assertEqual((await runtime.resume(run_id))['status'],'completed')
            self.assertEqual(runtime.agent.llm.calls[('generation','index.html')],1)
        finally:
            await runtime.aclose()

    async def test_interruption_persists_and_resumes(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_retries=0),delay=.08)
        try:
            run_id=runtime.create_run(self.case['profile'],pages=page_specs(self.case))
            work=asyncio.create_task(runtime.execute(run_id))
            while not runtime.agent.llm.active:
                await asyncio.sleep(.01)
            work.cancel()
            self.assertEqual((await work)['status'],'cancelled')
            await runtime.aclose()
            self.assertTrue(any(t['status']=='interrupted' for t in runtime.state.tasks(run_id)))
            self.assertEqual((await runtime.resume(run_id))['status'],'completed')
        finally:
            await runtime.aclose()

    async def test_budget_exhaustion_preserves_accounting_on_resume(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_prompt_tokens=100,max_concurrency=1,max_retries=0))
        try:
            run_id=runtime.create_run(self.case['profile'],pages=page_specs(self.case))
            first=await runtime.execute(run_id)
            self.assertEqual(first['status'],'budget_exceeded')
            self.assertEqual(first['usage']['prompt_tokens'],100)
            runtime.set_limits(run_id,replace(runtime.budget.limits,max_prompt_tokens=10000))
            result=await runtime.resume(run_id)
            self.assertEqual(result['status'],'completed')
            self.assertGreater(result['usage']['prompt_tokens'],100)
        finally:
            await runtime.aclose()


if __name__=='__main__':
    unittest.main()
