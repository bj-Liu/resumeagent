"""Regressions from real GUI debugging; no network or provider charges."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from examples.harness_demo import DemoBrowser
from harness.budget import BudgetLimits
from harness.runtime import Runtime, RunStopped
from resumeagent.main import HomepageDesignAgent


class DebugTests(unittest.TestCase):
    def test_visual_evaluation_accepts_real_json_envelopes_and_rejects_invalid_schema(self):
        from resumeagent.agents.refiner import Refiner
        agent = Refiner()
        agent.user_feedback = ''
        agent.language = 'zh'
        payload = '{"needs_refinement": true, "feedback": "Improve contrast"}'
        for response in (payload, f'```json\n{payload}\n```',
                         f'<evaluation>{payload}</evaluation>',
                         f'<evaluation>```json\n{payload}\n```</evaluation>'):
            agent.get_answer_async = AsyncMock(return_value=response)
            result = asyncio.run(agent.evaluate_screenshot_async({'html_name':'index.html'}, 'index.png'))
            self.assertTrue(result['needs_refinement'])
            self.assertEqual(result['feedback'], 'Improve contrast')
        for response in ('[]', '{"needs_refinement":"false"}', '{"needs_refinement":true,"feedback":[]}',
                         'prose {"needs_refinement":false}', 'not JSON'):
            agent.get_answer_async = AsyncMock(return_value=response)
            with self.assertRaises(ValueError):
                asyncio.run(agent.evaluate_screenshot_async({'html_name':'index.html'}, 'index.png'))

    def test_flash_cost_uses_million_token_units(self):
        from resumeagent.utils import cal_cost
        self.assertAlmostEqual(cal_cost(1_000_000, 1_000_000, 'qwen3.8-flash'), 3.5)
        self.assertAlmostEqual(cal_cost(889, 1418, 'qwen3.8-flash'), .0045398)

    def test_missing_provider_credential_keeps_original_traceback_and_task(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, LLM_TYPE='qwen',DASHSCOPE_API_KEY=''):
            agent = HomepageDesignAgent(model='qwen3.8-max', save_file=directory,
                                        browser=DemoBrowser())
            agent.task['basic_information'] = 'Example researcher'
            runtime = Runtime(agent, storage_root=Path(directory)/'state',
                              limits=BudgetLimits(max_retries=0))
            run_id = runtime.create_run(action={'method':'plan'})
            try:
                result = asyncio.run(runtime.execute(run_id))
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['error'], 'ValueError')
                task = runtime.state.tasks(run_id)[0]
                self.assertEqual(task['status'], 'failed')
                records = [json.loads(line) for line in runtime.tracer.diagnostic_path(run_id).read_text(encoding='utf-8').splitlines()]
                detail = next(item for item in records if item.get('task_id') == task['id'])
                self.assertEqual(detail['run_id'], run_id)
                self.assertEqual(detail['stage'], 'planning')
                self.assertIn('DASHSCOPE_API_KEY is not set', detail['message'])
                self.assertIn('in __init__', detail['traceback'])
                self.assertIn('in llm_call', detail['traceback'])
                self.assertIn('Developer diagnostics:', str(RunStopped(result, runtime.tracer.diagnostic_path(run_id))))
            finally:
                agent.close()

    def test_local_diagnostics_redact_credentials_profile_and_chained_errors(self):
        key = 'fixture-credential-that-must-stay-private'
        profile = 'fixture personal profile that must stay private'
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, OPENAI_API_KEY=key):
            agent = HomepageDesignAgent(save_file=directory, llm=object(), browser=DemoBrowser())
            runtime = Runtime(agent, storage_root=Path(directory)/'state')
            run_id = runtime.create_run({'basic_information':profile}, feedback='private fixture feedback')
            try:
                try:
                    raise RuntimeError(f'Provider rejected {key}')
                except RuntimeError as cause:
                    raise ValueError(f'Invalid input: {profile}') from cause
            except ValueError as exc:
                path = runtime.tracer.exception(run_id, exc, stage='planning')
            raw = path.read_text(encoding='utf-8')
            self.assertNotIn(key, raw)
            self.assertNotIn(profile, raw)
            self.assertIn('[REDACTED]', raw)
            self.assertIn('direct cause', raw)
            self.assertNotIn('traceback', json.dumps(runtime.tracer.query(run_id)))
            agent.close()


if __name__ == '__main__':
    unittest.main()
