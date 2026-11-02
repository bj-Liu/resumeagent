"""Actual parser/validators and unchanged agents; no real model or browser fees."""
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import importlib
import inspect
import io
import itertools
import json
from pathlib import Path
from string import Formatter
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from examples.harness_demo import DemoBrowser
from harness.budget import BudgetLimits
from harness.context import CURRENT_EXECUTION
from harness.runtime import Runtime
from resumeagent.llm import client
from resumeagent.main import HomepageDesignAgent
from resumeagent.prompts import planner
from resumeagent.prompts.planner_protocol import example_pages,output_contract,design_quality
from resumeagent.tools.filesystem import Filesystem
from resumeagent.utils import extract

FIELDS={'html_name','css_name','description','page_style','is_main_page','js_description',
        'practice_features','additional_features','relationship'}
PROFILE=dict(basic_information='张三，人工智能方向硕士研究生。',
             academic_achievements='研究方向：大语言模型、智能体系统、自动化决策。',
             experience='个人主页生成系统、多智能体执行框架。',
             professional_skills='Python、PyTorch、Transformer、RAG、Agent、Selenium、HTML、CSS。')


class ProtocolLLM:
    def __init__(self):
        self.calls=[]
    async def response_async(self,messages,**kwargs):
        scope=CURRENT_EXECUTION.get()
        self.calls.append(scope.stage)
        client.record_tokens(kwargs['model'],30,10)
        text=messages[-1]['content'][-1]['text']
        if scope.stage=='planning':
            tag='modified_page' if '<modified_page>' in text else 'designed_pages'
            return f'<{tag}>'+extract(text,tag)+f'</{tag}>'
        if scope.stage=='evaluation':
            return '<evaluation>{"needs_refinement":false,"feedback":""}</evaluation>'
        page=scope.runtime.state.page(scope.page_id)['spec']
        return ('```html\n<!doctype html><html><head><meta charset="utf-8"><title>Protocol fixture</title>'
                +f'<link rel="stylesheet" href="{page.get("css_name", "index.css")}"></head>'
                '<body><h1>Protocol fixture</h1><a href="index.html">Home</a><a href="projects.html">Projects</a></body></html>\n```\n'
                '```css\nbody { color: #202522; }\n```')


class PlannerProtocolTests(unittest.TestCase):
    def test_existing_validator_minimum_is_not_a_new_mandatory_schema(self):
        Filesystem.validate_plan([{'html_name':'index.html'}])
        Filesystem.validate_page_spec({'html_name':'safe/sub/page.HTML','css_name':'safe/sub/page.CSS'})
        # Optional business data is not checked by this validator. Do not mistake
        # recommended model output types for validator requirements.
        Filesystem.validate_page_spec({'html_name':'index.html','relationship':'legacy text'})
        for bad in ('../index.html','nested/../index.html','F:/index.html','index.css'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                Filesystem.validate_page_spec({'html_name':bad})
        with self.assertRaises(ValueError):
            Filesystem.validate_plan([{'html_name':'Index.html'},{'html_name':'index.html'}])
        with self.assertRaises(ValueError):
            Filesystem.validate_plan([])
        # On Windows, '/index.html' is rooted but has no drive, so is_absolute()
        # in the old validator is false. The real output confinement still rejects it.
        with tempfile.TemporaryDirectory() as folder:
            agent=HomepageDesignAgent(save_file=folder,llm=object(),browser=MagicMock())
            with self.assertRaises(ValueError):
                agent.page_paths({'html_name':'/index.html'})
            agent.close()

    def test_bilingual_examples_have_identical_types_and_different_page_compositions(self):
        def shape(value):
            if isinstance(value,dict):return {k:shape(v) for k,v in value.items()}
            if isinstance(value,list):return [shape(v) for v in value]
            return type(value).__name__
        self.assertEqual(shape(example_pages('zh')),shape(example_pages('en')))
        for language in ('zh','en'):
            pages=example_pages(language)
            Filesystem.validate_plan(pages)
            for page in pages:
                self.assertEqual(set(page),FIELDS)
                self.assertEqual(type(page['is_main_page']),bool)
                self.assertIsInstance(page['relationship'],dict)
                self.assertTrue(all(isinstance(page[key],str) for key in FIELDS-{'relationship','is_main_page'}))
                self.assertGreater(len(page['description']),180)
                self.assertGreater(len(page['page_style']),180)
            self.assertNotEqual(pages[0]['description'],pages[1]['description'])
            self.assertEqual(sum(page['is_main_page'] for page in pages),1)
            self.assertEqual(pages[0]['relationship'],pages[1]['relationship'])

    def test_full_language_framework_image_matrix_is_exactly_one_real_json_array(self):
        for language,frame,local in itertools.product(('zh','en'),(None,'Tailwind','Bootstrap','Boostrap','Materialize','Bulma'),([], [{'img_path':'images/portrait.png'}])):
            with self.subTest(language=language,frame=frame,local=bool(local)):
                prompt=planner.get_plan_prompt(**PROFILE,language=language,css_frame=frame,local_img_storage=local,
                                               img='reference.png',feedback='Preserve {literal braces} and "quotes"')
                self.assertEqual(prompt.count('<designed_pages>'),1)
                self.assertEqual(prompt.count('</designed_pages>'),1)
                payload=extract(prompt,'designed_pages')
                self.assertNotIn('```',payload)
                pages=json.loads(payload)
                Filesystem.validate_plan(pages)
                self.assertEqual(set(pages[0]),FIELDS-({'css_name'} if frame else set()))
                with tempfile.TemporaryDirectory() as folder:
                    agent=HomepageDesignAgent(save_file=folder,llm=object(),browser=MagicMock())
                    agent.css_frame=frame
                    for page in pages:
                        paths=agent.page_paths(page)
                        self.assertEqual('css' in paths,not bool(frame))
                        if local:
                            self.assertEqual(page['relationship']['imgs'],[])
                    agent.close()
                self.assertIn('USER FACTS',prompt)
                self.assertIn('NaN',prompt)
                self.assertIn('html_name',prompt)
                self.assertIn('jump_page',prompt)

    def test_edit_and_completion_examples_preserve_actual_filenames_and_keys(self):
        for language in ('zh','en'):
            for frame in (None,'Tailwind'):
                page=example_pages(language)[1]
                if frame:page.pop('css_name')
                before=deepcopy(page)
                edited=planner.get_refine_page_prompt('Facts',page,css_frame=frame,language=language)
                self.assertEqual(json.loads(extract(edited,'modified_page')),page)
                complete=planner.get_page_complete_prompt('Facts','Other',json.dumps(page),language=language)
                self.assertEqual(json.loads(extract(complete,'completed_page')),page)
                self.assertEqual(json.loads(extract(complete,'page_relationship')),[])
                self.assertEqual(page,before)

    def test_format_fields_are_only_explicit_placeholders_and_templates_keep_legacy_exports(self):
        expected={
            'plan_output_format_prompt':{'page_template'},
            'plan_output_format_prompt_local_img':{'page_template','local_img_storage'},
            'refine_page_prompt':{'task_info','page_info','page_example','feedback'},
            'refine_page_local_img_prompt':{'task_info','page_info','page_example','feedback','local_img_storage'},
            'page_complete_prompt':{'task_info','other_pages_info','page_info','feedback','page_example'},
            'page_complete_prompt_local_img':{'task_info','other_pages_info','page_info','feedback','page_example','local_img_storage'},
        }
        for language in ('zh','en'):
            module=importlib.import_module('resumeagent.prompts.plan_prompts_'+language)
            for name,fields in expected.items():
                with self.subTest(language=language,name=name):
                    actual={field for _,field,_,_ in Formatter().parse(getattr(module,name)) if field is not None}
                    self.assertEqual(actual,fields)
            for name in ('original_page_template','local_img_storage_page_template'):
                Filesystem.validate_plan(json.loads(getattr(module,name)))

    def test_unchanged_agent_parses_both_languages_then_builds_generator_and_refiner_inputs(self):
        for language in ('zh','en'):
            for frame in (None,'Tailwind'):
                with tempfile.TemporaryDirectory() as folder:
                    agent=HomepageDesignAgent(save_file=folder,llm=object(),browser=MagicMock())
                    agent.task.update(PROFILE);agent.language=language;agent.css_frame=frame
                    async def respond(messages):
                        text=messages[-1]['content'][-1]['text']
                        tag='modified_page' if '<modified_page>' in text else 'designed_pages'
                        return f'<{tag}>'+extract(text,tag)+f'</{tag}>'
                    agent.get_answer_async=AsyncMock(side_effect=respond)
                    with redirect_stdout(io.StringIO()):
                        pages=asyncio.run(agent.plan_async(reuse_cached=False))
                    self.assertEqual(agent.get_answer_async.await_count,3) # One plan + two existing spec refinements.
                    self.assertEqual(len(pages),2)
                    self.assertEqual(json.loads((Path(folder)/'pages.json').read_text(encoding='utf-8')),pages)
                    for page in pages:
                        self.assertIn(page['description'],str(agent.get_write_original_website_messages(page)))
                        paths=agent.page_paths(page)
                        Path(paths['html']).write_text('<html>Fixture</html>',encoding='utf-8')
                        if 'css' in paths:Path(paths['css']).write_text('body{}',encoding='utf-8')
                        self.assertIn(page['html_name'],str(agent.get_refine_messages(page)))
                    agent.close()

    def test_harness_workflow_with_real_agents_and_mock_llm_preserves_state_and_code_protocol(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(client,'token_log_file',str(Path(folder)/'tokens.json')):
            backend=ProtocolLLM()
            agent=HomepageDesignAgent(model='protocol-fixture',save_file=str(Path(folder)/'site'),llm=backend,browser=DemoBrowser())
            agent.task.update(PROFILE);agent.language='zh';agent.css_frame=None;agent.gen_img=False
            agent.execution_mode='mock';agent.rendering_mode='simulated'
            runtime=Runtime(agent,storage_root=Path(folder)/'state',limits=BudgetLimits(max_retries=0,max_iterations=1))
            run_id=runtime.create_run(output_dir=agent.save_file)
            with redirect_stdout(io.StringIO()):result=asyncio.run(runtime.execute(run_id))
            self.assertEqual(result['status'],'completed',result['error'])
            self.assertEqual(len(runtime.state.pages(run_id)),2)
            for page in runtime.state.pages(run_id):
                self.assertTrue(all(Path(path).is_file() for path in page['files'].values()))
                self.assertEqual(page['status'],'completed')
            self.assertEqual(backend.calls.count('planning'),3)
            self.assertEqual(backend.calls.count('generation'),2)
            agent.runtime_options={'storage_root':str(Path(folder)/'state'),'limits':BudgetLimits(max_retries=0)}
            agent.managed_action('refine',result['context']['plan'][0])
            self.assertEqual(agent._runtime().state.get_run(agent.last_run_id)['status'],'completed')
            agent.close()

    def test_parser_rejects_fences_python_objects_duplicate_blocks_and_bad_paths_without_relaxation(self):
        valid=json.dumps(example_pages('en'))
        for raw in (f'```json\n{valid}\n```',str(example_pages('en')),f'{valid}{valid}','[{page specification objects}]'):
            with self.subTest(raw=raw[:30]),self.assertRaises(ValueError):
                json.loads(extract('<designed_pages>'+raw+'</designed_pages>','designed_pages'))
        self.assertEqual(extract(valid,'designed_pages'),'')
        for filename in ('../outside.html','C:/outside.html'):
            bad=example_pages('en');bad[0]['html_name']=filename
            with self.assertRaises(ValueError):Filesystem.validate_plan(bad)

    def test_public_prompt_parameter_names_remain_unchanged(self):
        expected={
            'get_plan_prompt':('basic_information','academic_achievements','experience','professional_skills','refine_times','img','css_frame','feedback','language','status','industry','local_img_storage'),
            'get_refine_page_prompt':('task','page_info','css_frame','feedback','language','local_img_storage'),
            'get_page_complete_prompt':('task','other_pages_info','page_info','feedback','language','local_img_storage'),
        }
        for name,parameters in expected.items():
            self.assertEqual(tuple(inspect.signature(getattr(planner,name)).parameters),parameters)
