"""Workflow acceptance and benchmark arithmetic. No paid API calls."""
import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from evals.support import load_cases, runtime_factory
from evals.benchmark import run_benchmark, summarize, validate_html
from harness.budget import BudgetLimits
from resumeagent.llm import client


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        patcher=patch.object(client,'token_log_file',str(self.root/'tokens.json'))
        patcher.start();self.addCleanup(patcher.stop)
        self.case=load_cases()[0]

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration=5

    async def test_planning_html_artifacts_render_and_visual_iterations(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_iterations=2))
        try:
            run_id=runtime.create_run(self.case['profile'],feedback=self.case['feedback'])
            result=await runtime.execute(run_id)
            self.assertEqual(result['status'],'completed')
            self.assertEqual(len(runtime.state.get_run(run_id)['context']['plan']),3)
            for page in runtime.state.pages(run_id):
                self.assertTrue(validate_html(page['files']['html'],result['files']['output_dir']))
                with Image.open(page['files']['screenshot']) as image:
                    image.verify()
                stages=[t['stage'] for t in runtime.state.tasks(run_id) if t['page_id']==page['id']]
                self.assertEqual(stages,['generation','rendering','evaluation','refinement','rendering','evaluation','validation'])
            self.assertTrue((Path(result['files']['output_dir'])/'pages.json').is_file())
        finally:
            await runtime.aclose()

    async def test_benchmark_outputs_measured_paired_statistics(self):
        report,path=await run_benchmark(self.root/'report',case_ids=['engineer'],recovery=True)
        self.assertTrue(path.is_file())
        self.assertEqual(report['token_source'],'synthetic_fixture_usage')
        self.assertEqual(len(report['primary_runs']),2)
        self.assertEqual(len({r['input_sha256'] for r in report['primary_runs']}),1)
        for variant in ('baseline','refined'):
            measured=[r for r in report['primary_runs'] if r['variant']==variant]
            self.assertEqual(report['variants'][variant]['prompt_tokens'],sum(r['prompt_tokens'] for r in measured))
            self.assertEqual(report['variants'][variant]['task_success_rate'],1)
            self.assertEqual(report['variants'][variant]['recovery_success_rate'],1)
            self.assertIsNone(report['variants'][variant]['api_cost_actual'])
            self.assertIsNone(report['variants'][variant]['visual_quality_score'])
        self.assertGreater(report['variants']['refined']['average_iterations_per_expected_page'],report['variants']['baseline']['average_iterations_per_expected_page'])

    async def test_metrics_do_not_turn_failures_into_success_or_visual_scores(self):
        record={'status':'failed','pages_expected':3,'pages_generated':2,'pages_completed':1,
                'wall_seconds':2,'prompt_tokens':100,'completion_tokens':40,'api_cost_estimate':.1,
                'refinement_calls':1,'html_validation_passes':1}
        result=summarize([record],[{'recovered':False}])
        self.assertEqual(result['task_success_rate'],0)
        self.assertEqual(result['page_generation_success_rate'],2/3)
        self.assertEqual(result['html_validation_pass_rate'],1/3)
        self.assertEqual(result['recovery_success_rate'],0)
        self.assertIsNone(result['visual_quality_score'])

    async def test_html_validation_rejects_broken_local_links(self):
        file=self.root/'index.html'
        file.write_text('<!doctype html><html><head><title>Test</title></head><body><a href="missing.html">Missing</a></body></html>')
        self.assertFalse(validate_html(file,self.root))

    @unittest.skipUnless(os.environ.get('RESUMEAGENT_REAL_BROWSER'),'Opt-in real Selenium test; no real LLM')
    async def test_real_selenium_with_mock_llm(self):
        runtime=runtime_factory(self.root,self.case,limits=BudgetLimits(max_iterations=0),browser=os.environ['RESUMEAGENT_REAL_BROWSER'])
        try:
            run_id=runtime.create_run(self.case['profile'])
            self.assertEqual((await runtime.execute(run_id))['status'],'completed')
        finally:
            await runtime.aclose()


if __name__=='__main__':
    unittest.main()
