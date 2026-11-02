import asyncio
import copy
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from PIL import Image
from resumeagent.llm import client
from resumeagent.tools.browser import Webserver
from resumeagent.main import HomepageDesignAgent

class AdapterTests(unittest.TestCase):
    def test_openai_sync_and_async_adapter(self):
        response=NS(usage=NS(prompt_tokens=3,completion_tokens=4),choices=[NS(message=NS(content='answer'))])
        messages=[{'role':'user','content':[{'type':'text','text':'Profile'}]}]
        with patch.dict('os.environ',{'is_azure':'false','OPENAI_API_KEY':'test-only'}), patch('openai.OpenAI') as sync, patch('openai.AsyncOpenAI') as async_, patch.object(client,'record_tokens') as record:
            sync.return_value.chat.completions.create.return_value=response
            async_.return_value.chat.completions.create=AsyncMock(return_value=response)
            adapter=client.openai_llm()
            self.assertEqual(adapter.response(messages,model='original-model',max_tokens=50),'answer')
            self.assertEqual(asyncio.run(adapter.response_async(messages,model='original-model')),'answer')
            self.assertEqual(sync.return_value.chat.completions.create.call_args.kwargs['max_tokens'],50)
            self.assertEqual(record.call_count,2)

    def test_azure_adapter_preserves_endpoint_and_deployment(self):
        with patch.dict('os.environ',{'is_azure':'true','AZURE_OPENAI_ENDPOINT':'https://example.invalid','AZURE_OPENAI_KEY':'test-only','AZURE_OPENAI_API_VERSION':'2024-02-01'}), patch('openai.AzureOpenAI') as sync, patch('openai.AsyncAzureOpenAI'):
            adapter=client.openai_llm()
            self.assertEqual(sync.call_args.kwargs['azure_endpoint'],'https://example.invalid')
            self.assertEqual(adapter._params([],{'model':'deployment-name'})['model'],'deployment-name')

    def test_qwen_text_and_multimodal_routing(self):
        response=NS(usage=NS(input_tokens=2,output_tokens=3),output=NS(choices=[NS(message=NS(content='answer'))]))
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ',{'DASHSCOPE_API_KEY':'test-only'}), patch('dashscope.Client') as factory, patch.object(client,'record_tokens'):
            image_path=str(Path(folder)/'fixture.png')
            Image.new('RGB',(2,2),'white').save(image_path)
            api=factory.return_value.multimodal.chat.create
            api.return_value=response
            adapter=client.qwen_llm()
            self.assertEqual(adapter.response([{'role':'user','content':[{'type':'text','text':'Profile'}]}],model='qwen3.8-max'),'answer')
            self.assertEqual(api.call_args.kwargs['model'],'qwen3.8-max')
            messages=[{'role':'user','content':[{'type':'image','url':image_path},{'type':'text','text':'Feedback'}]}]
            original=copy.deepcopy(messages)
            self.assertEqual(asyncio.run(adapter.response_async(messages,model='qwen3.8-max')),'answer')
            sent=api.call_args.kwargs['messages'][0]['content']
            self.assertEqual(sent[0]['image'],client.get_openai_url(image_path))
            self.assertEqual(sent[1],{'text':'Feedback'})
            self.assertEqual(messages,original)
            self.assertNotIn('preserve_thinking',api.call_args.kwargs)

    def test_selenium_rendering_boundary_and_preview_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            html=Path(folder)/'page with spaces.html'; html.write_text('<html><body>Profile</body></html>')
            driver=MagicMock()
            events=[]
            driver.set_window_size.side_effect=lambda *args:events.append('resize')
            driver.execute_script.side_effect=lambda script:'complete' if 'readyState' in script else 1200
            def save(path):
                events.append('screenshot')
                Image.new('RGB',(1440,1200)).save(path)
                return True
            driver.save_screenshot.side_effect=save
            browser=Webserver(folder,web_type='chrome')
            with patch.object(browser,'_create_driver',return_value=driver),patch('resumeagent.tools.browser.time.sleep',side_effect=lambda _:events.append('wait')):
                screenshot=browser.get_screenshot(str(html))
                self.assertTrue(Path(screenshot).exists())
                self.assertEqual(events, ['resize','wait','resize','wait','screenshot'])
                driver.get.assert_called_with(html.resolve().as_uri())
                browser.open_website(str(html))
                browser.stop()
                self.assertEqual(driver.quit.call_count,2)
                self.assertIsNone(browser.preview_driver)

    def test_qwen_current_sdk_flat_completion_sync_async_and_usage(self):
        from dashscope.types.completions import ChatCompletion
        response = ChatCompletion.model_validate({
            'model':'qwen3.8-flash',
            'choices':[{'message':{'role':'assistant','content':'<designed_pages>[]</designed_pages>'}}],
            'usage':{'input_tokens':12,'output_tokens':7,'total_tokens':19},
        })
        self.assertFalse(hasattr(response, 'output'))
        adapter = client.qwen_llm.__new__(client.qwen_llm)
        adapter.client = MagicMock()
        adapter.client.with_options.return_value = adapter.client
        api = adapter.client.multimodal.chat.create
        api.return_value = response
        messages = [{'role':'user','content':[{'type':'text','text':'Profile'}]}]
        with patch.object(client, 'record_tokens') as record:
            for answer in (adapter.response(messages, model='qwen3.8-flash', _max_attempts=1),
                           asyncio.run(adapter.response_async(messages, model='qwen3.8-flash', _max_attempts=1))):
                self.assertEqual(answer, '<designed_pages>[]</designed_pages>')
            self.assertEqual(record.call_args_list, [unittest.mock.call('qwen3.8-flash',12,7)]*2)
            self.assertEqual(adapter.response(messages, _max_attempts=1), '<designed_pages>[]</designed_pages>')
            self.assertEqual(record.call_count, 3)
        self.assertEqual(api.call_count, 3)
        self.assertEqual(api.call_args.kwargs['model'], 'qwen3.8-flash')
        self.assertEqual(api.call_args.kwargs['temperature'], .3)
        self.assertEqual(api.call_args.kwargs['top_p'], .7)

    def test_qwen_legacy_list_content_and_empty_choices_accounting(self):
        adapter = client.qwen_llm.__new__(client.qwen_llm)
        adapter.client = MagicMock()
        adapter.client.with_options.return_value = adapter.client
        response = NS(usage=NS(input_tokens=4,output_tokens=2),
                      output=NS(choices=[NS(message=NS(content=[{'text':'one'},{'text':'two'}]))]))
        api = adapter.client.multimodal.chat.create
        api.return_value = response
        with patch.object(client, 'record_tokens') as record:
            self.assertEqual(adapter.response([], model='qwen3.8-flash', _max_attempts=1), 'onetwo')
            record.assert_called_once_with('qwen3.8-flash',4,2)
        adapter.client.with_options.return_value = adapter.client
        api.return_value = NS(usage=NS(input_tokens=8,output_tokens=1), choices=[])
        with patch.object(client, 'record_tokens') as record:
            with self.assertRaisesRegex(ValueError, 'no choices'):
                adapter.response([], model='qwen3.8-flash', _max_attempts=1)
            record.assert_called_once_with('qwen3.8-flash',8,1)

    def test_qwen_local_screenshot_is_inlined_without_oss_upload(self):
        import base64
        adapter = client.qwen_llm.__new__(client.qwen_llm)
        with tempfile.TemporaryDirectory() as folder:
            screenshot = Path(folder)/'screenshot with spaces.png'
            Image.new('RGB', (20, 30), 'blue').save(screenshot)
            for reference in (str(screenshot), screenshot.resolve().as_uri()):
                messages = [{'role':'user','content':[{'type':'image','url':reference},
                                                      {'type':'text','text':'Evaluate layout'}]}]
                original = copy.deepcopy(messages)
                converted = adapter._convert_messages(messages)
                image_url = converted[0]['content'][0]['image']
                self.assertTrue(image_url.startswith('data:image/png;base64,'))
                self.assertEqual(base64.b64decode(image_url.split(',',1)[1]), screenshot.read_bytes())
                self.assertEqual(converted[0]['content'][1], {'text':'Evaluate layout'})
                self.assertEqual(messages, original)
            remote = 'https://example.invalid/image.png'
            converted = adapter._convert_messages([{'role':'user','content':[{'type':'image','url':remote}]}])
            self.assertEqual(converted[0]['content'][0]['image'], remote)

    def test_local_image_description_and_provider_hook(self):
        with tempfile.TemporaryDirectory() as folder:
            image=Path(folder)/'avatar.png'; Image.new('RGB',(12,15)).save(image)
            backend=MagicMock(); backend.response_async=AsyncMock(return_value='<Chinese>头像</Chinese><English>Avatar</English>')
            agent=HomepageDesignAgent(save_file=folder,llm=backend,browser=MagicMock())
            asyncio.run(agent.add_img_to_storage_async(str(image)))
            self.assertEqual(agent.local_img_storage_en[0]['description'],'Avatar')
            self.assertEqual(agent.local_img_storage_zh[0]['width'],12)
            provider=MagicMock(); provider.get_img.return_value=Image.new('RGB',(8,8))
            agent.image_client=provider
            content=agent.save_img(agent.get_img('portrait'),{'src':'nested/portrait.png'})
            self.assertEqual(content['src'],'portrait.png')
            self.assertTrue((Path(folder)/'portrait.png').exists())

if __name__=='__main__':
    unittest.main()
