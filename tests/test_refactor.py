"""Offline regression tests: real orchestration, controlled model/browser boundaries."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from resumeagent.main import HomepageDesignAgent
from resumeagent.prompts.planner import get_plan_prompt
from resumeagent.prompts.generator import get_write_original_website_prompt
from resumeagent.prompts.refiner import get_refine_prompt
from resumeagent.llm import client

PAGES = [dict(html_name=name, css_name=name.replace('.html','.css'), description='Profile',
              is_main_page=i == 0, relationship={'buttons': [], 'links': []}, page_style='Clean')
         for i, name in enumerate(['index.html','projects.html'])]
HTML = '```html\n<html><body><a href="projects.html">Profile</a></body></html>\n```\n```css\nbody {color: blue;}\n```'

class FakeBrowser:
    def __init__(self):
        self.shots = []
    def get_screenshot(self, html, save_path, is_local=True):
        assert Path(html).is_file()
        Image.new('RGB', (64,64), 'white').save(save_path)
        self.shots.append((str(html), str(save_path)))
    def stop(self):
        pass

class FakeLLM:
    def __init__(self):
        self.active = self.peak = 0
        self.vision = []
        self.sync_calls = 0
    def response(self, messages, **kwargs):
        self.sync_calls += 1
        text = messages[-1]['content'][-1]['text']
        if '<designed_pages>' in text:
            return '<designed_pages>'+json.dumps(PAGES)+'</designed_pages>'
        if '<modified_page>' in text:
            page = PAGES[1] if 'projects.html' in text.split('Page:')[-1] else PAGES[0]
            return '<modified_page>'+json.dumps(page)+'</modified_page>'
        return HTML
    async def response_async(self, messages, **kwargs):
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(.02)
            client.record_tokens(kwargs.get('model','test-model'),10,5)
            text = messages[-1]['content'][-1]['text']
            if '<designed_pages>' in text:
                return '<designed_pages>'+json.dumps(PAGES)+'</designed_pages>'
            if '<evaluation>' in text:
                return '<evaluation>{"needs_refinement": true, "feedback": "spacing"}</evaluation>'
            if '<modified_page>' in text:
                # Refine-page templates contain examples; use final current-page section.
                page = PAGES[1] if "'html_name': 'projects.html'" in text else PAGES[0]
                return '<modified_page>'+json.dumps(page)+'</modified_page>'
            images = [b['url'] for b in messages[-1]['content'] if b['type'] == 'image']
            for image in images:
                assert Path(image).is_file()
            if images:
                self.vision.append(images)
            return HTML
        finally:
            self.active -= 1

class RefactorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch.object(client, 'token_log_file', str(Path(self.temp.name)/'tokens.json'))
        patcher.start(); self.addCleanup(patcher.stop)
        self.browser = FakeBrowser()
        self.llm = FakeLLM()
        self.agent = HomepageDesignAgent(save_file=self.temp.name, llm=self.llm, browser=self.browser, runtime_options={'storage_root':str(Path(self.temp.name)/'storage')})
        self.agent.gen_img = False

    def test_full_pipeline_multpage_concurrency_and_visual_iterations(self):
        self.agent.act(basic_information='Test profile', feedback='Blue header', refine_times=2)
        self.assertGreaterEqual(self.llm.peak, 2)
        self.assertEqual(len(self.browser.shots), 6)
        self.assertEqual(len(self.llm.vision), 4)
        self.assertEqual([p['html_name'] for p in self.agent.task_queue], ['index.html','projects.html'])
        for name in ('index.html','projects.html','index.png','projects.png','pages.json'):
            self.assertTrue((Path(self.temp.name)/name).exists())
        self.assertEqual(self.agent.user_feedback, 'Blue header')
        self.assertEqual(self.agent.plan(), self.agent.task_queue)  # cached pages

    def test_separate_css_sync_and_async(self):
        self.agent.css_frame = None
        self.agent.publish_task(basic_information='Profile')
        self.agent.write_original_website(PAGES[0])
        asyncio.run(self.agent.write_original_website_async(PAGES[1]))
        self.assertIn('blue', (Path(self.temp.name)/'index.css').read_text())
        self.assertTrue((Path(self.temp.name)/'projects.css').exists())

    def test_css_retry_is_bounded(self):
        self.agent.css_frame = None
        async def invalid_response(*a, **k):
            return '```html\n<html></html>\n```'
        self.agent.llm.response_async = invalid_response
        with self.assertRaises(AssertionError):
            self.agent.write_original_website(PAGES[0])

    def test_feedback_and_bilingual_framework_prompts(self):
        for language in ('en','zh'):
            self.assertIn('FEEDBACK',get_plan_prompt(basic_information='Profile', feedback='FEEDBACK', language=language))
            for framework in ('Tailwind','Bootstrap','Boostrap','Materialize','Bulma',None):
                generated = get_write_original_website_prompt(page_info=PAGES[0], css_frame=framework, language=language)
                refined = get_refine_prompt(page_info=PAGES[0], css_frame=framework, language=language, html_code='CODE', feedback='FEEDBACK')
                self.assertIn('FEEDBACK', refined)
                self.assertIn('CODE', refined)
                if framework in ('Bootstrap','Boostrap'):
                    self.assertIn('bootstrap', generated.lower())

    def test_text_only_refinement_and_reference_image(self):
        self.agent.publish_task(basic_information='Profile', img='reference.png')
        self.agent.update_html_css(PAGES[0], '<html></html>',None)
        messages = self.agent.get_refine_messages(PAGES[0])
        self.assertEqual([b['url'] for b in messages[0]['content'] if b['type']=='image'], ['reference.png', str(Path(self.temp.name)/'index.png')])
        self.agent.vision = False
        self.assertFalse(any(b['type']=='image' for b in self.agent.get_refine_messages(PAGES[0])[0]['content']))

    def test_page_edit_and_completion(self):
        self.agent.publish_task(basic_information='Profile')
        refined = self.agent.refine_page(PAGES[0], 'Change header')
        self.assertEqual(refined['html_name'],'index.html')
        completed = copy.deepcopy(PAGES[1]); completed['description']='Completed'
        response='<completed_page>'+json.dumps(completed)+'</completed_page><page_relationship>[{"html_name":"index.html","button_name":"Projects"}]</page_relationship>'
        self.agent.llm.response = lambda *a, **k: response
        pages=self.agent.complete_page(copy.deepcopy(PAGES),1)
        self.assertEqual(pages[1]['description'],'Completed')
        self.assertEqual(pages[0]['relationship']['buttons'][0]['jump_page'],'projects.html')

    def test_zero_iterations_and_output_directory(self):
        self.agent.publish_task(refine_times=0)
        self.assertEqual(self.agent.refine_times,0)
        folder=str(Path(self.temp.name)/'new')
        self.agent.change_save_file(folder)
        self.assertEqual(self.browser.save_file,folder)

    def test_cleanup_preserves_page_screenshot_and_referenced_images(self):
        p=Path(self.temp.name)
        self.agent.task_queue=[PAGES[0]]
        (p/'index.html').write_text('<img src="avatar.png">')
        for name in ('index.png','avatar.png','unused.png'):
            Image.new('RGB',(8,8)).save(p/name)
        self.agent.clean()
        self.assertTrue((p/'index.png').exists())
        self.assertTrue((p/'avatar.png').exists())
        self.assertFalse((p/'unused.png').exists())

    def test_token_logging_concurrent_and_new_model(self):
        with patch.object(client,'token_log_file',str(Path(self.temp.name)/'tokens.json')):
            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(lambda _:client.record_tokens('new-model',1,2),range(40)))
            self.assertEqual(client.read_tokens(),{'new-model':[40,80]})

    def test_openai_message_translation_without_mutation(self):
        p=Path(self.temp.name)/'ref.png'; Image.new('RGB',(8,8)).save(p)
        messages=[{'role':'user','content':[{'type':'image','url':str(p)},{'type':'text','text':'Profile'}]}]
        before=copy.deepcopy(messages)
        result=client.base_llm().process_messages(messages)
        self.assertTrue(result[0]['content'][0]['image_url']['url'].startswith('data:image/png;base64,'))
        self.assertEqual(messages,before)

    def test_current_public_entrypoints(self):
        import importlib
        from resumeagent.tools.browser import Webserver
        from resumeagent.frontend.gui import Application
        from resumeagent.llm.client import get_llm
        from resumeagent.main import main
        self.assertIs(importlib.import_module('main').main, main)
        self.assertTrue(callable(main))
        self.assertTrue(callable(get_llm))
        self.assertTrue(callable(Application))
        self.assertTrue(callable(Webserver))
        self.assertTrue(callable(get_plan_prompt))

    def test_gui_startup_and_input_mapping(self):
        import subprocess
        import sys
        script=Path(__file__).with_name('gui_smoke.py')
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('GUI_SMOKE_OK',result.stdout)


if __name__ == '__main__':
    unittest.main()
