"""Reproducible offline Run example. --real-browser uses real Selenium with a fake LLM."""
import argparse
import asyncio
import html
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from harness.context import CURRENT_EXECUTION
from harness.budget import BudgetLimits
from harness.runtime import Runtime
from resumeagent.main import HomepageDesignAgent
from resumeagent.llm import client

DEMO_PAGES = [
    {'html_name':name, 'css_name':name.replace('.html','.css'), 'description':description,
     'is_main_page':i == 0, 'page_style':'Readable blue and white cards',
     'relationship':{'buttons':[], 'links':[{'link_name':'Home','jump_page':'index.html'}]}}
    for i,(name,description) in enumerate([('index.html','Demo profile'),('projects.html','Demo projects'),('skills.html','Demo skills')])]


class DemoLLM:
    def __init__(self, delay=.01, fail_page=None, fail_times=0, needs_refinement=True):
        self.delay, self.fail_page, self.fail_times = delay, fail_page, fail_times
        self.needs_refinement = needs_refinement
        self.calls = []
        self.active = self.peak = 0

    async def response_async(self, messages, **kwargs):
        self.active += 1
        self.peak = max(self.peak,self.active)
        try:
            await asyncio.sleep(self.delay)
            scope = CURRENT_EXECUTION.get()
            page = scope.runtime.state.page(scope.page_id) if scope.page_id else None
            name = page['spec']['html_name'] if page else ''
            self.calls.append((scope.stage,name))
            if scope.stage == 'generation' and name == self.fail_page and self.fail_times:
                self.fail_times -= 1
                raise RuntimeError('Simulated provider error with private profile and sk-DO-NOT-LOG')
            client.record_tokens(kwargs.get('model','demo-model'),100,40)
            text = messages[-1]['content'][-1]['text']
            if scope.stage == 'planning':
                if '<modified_page>' in text:
                    spec = next((p for p in DEMO_PAGES if f"'html_name': '{p['html_name']}'" in text),DEMO_PAGES[0])
                    return '<modified_page>'+json.dumps(spec)+'</modified_page>'
                return '<designed_pages>'+json.dumps(DEMO_PAGES)+'</designed_pages>'
            if scope.stage == 'evaluation':
                return '<evaluation>'+json.dumps({'needs_refinement':self.needs_refinement and page['iteration'] < 1,'feedback':'Increase spacing and make navigation clear.'})+'</evaluation>'
            navigation = ''.join(f'<a href="{p["html_name"]}">{html.escape(p["description"])}</a> ' for p in DEMO_PAGES)
            title = html.escape(page['spec']['description'])
            document = f'''<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
            <style>body{{font:20px system-ui;margin:60px;color:#16304c;background:#eff6ff}}nav a{{margin-right:24px}}main{{background:white;padding:40px;margin-top:36px;border-radius:16px}}</style>
            </head><body><nav>{navigation}</nav><main><h1>{title}</h1><p>Ada Example — fictional profile for the offline Harness demo.</p><p>Iteration {page['iteration']}</p></main></body></html>'''
            return '```html\n'+document+'\n```\n```css\nbody {color: #16304c;}\n```'
        finally:
            self.active -= 1


class DemoBrowser:
    """Test double: creates a valid PNG, does not claim to render HTML."""
    def __init__(self):
        self.calls = []

    def get_screenshot(self, html_path, save_path):
        if not Path(html_path).is_file():
            raise FileNotFoundError(html_path)
        self.calls.append(Path(html_path).name)
        image = Image.new('RGB',(800,450),'#eff6ff')
        ImageDraw.Draw(image).text((40,40),'OFFLINE DEMO - simulated browser screenshot',fill='#16304c')
        Path(save_path).parent.mkdir(parents=True,exist_ok=True)
        image.save(save_path)

    def open_website(self, html_path):
        pass

    def stop(self):
        pass


async def demo(args):
    root = Path(args.storage_root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    client.token_log_file = str(root/'demo-token.json')
    backend = DemoLLM(fail_page='projects.html' if args.fail_once else None,fail_times=1)
    if args.real_browser:
        from resumeagent.tools.browser import Webserver
        browser = Webserver(web_type=args.browser)
    else:
        browser = DemoBrowser()
    agent = HomepageDesignAgent(model='demo-model',save_file=str(root/'outputs'),llm=backend,browser=browser)
    agent.gen_img = False
    runtime = Runtime(agent,storage_root=root,limits=BudgetLimits(max_iterations=2,max_concurrency=2,max_retries=0))
    run_id = runtime.create_run({'basic_information':'Ada Example, fictional demo profile'})
    print('Browser:', 'real Selenium' if args.real_browser else 'simulated PNG (no rendering)')
    print('LLM: simulated responses; costs use the configured/legacy estimate')
    print('Run created:',run_id)
    try:
        result = await runtime.execute(run_id)
        print('First execution:',result['status'])
        if args.fail_once:
            print('Page checkpoints:',[(p['spec']['html_name'],p['status'],p['stage']) for p in runtime.state.pages(run_id)])
            result = await runtime.resume(run_id)
            print('After resume:',result['status'])
        for event in runtime.tracer.query(run_id):
            if event['event'] in {'run.created','run.started','task.started','task.completed','task.failed','page.skipped','page.completed','run.finished'}:
                print(event['event'],event.get('stage',''),event.get('status',''),event.get('page_id','')[:8])
        print('Usage:',json.dumps(result['usage']))
        print('Output:',result['files']['output_dir'])
        print('Query: python main.py --storage_root',str(root),'--trace',run_id)
        return 0 if result['status'] == 'completed' else 1
    finally:
        agent.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--storage_root',default='test-artifacts/harness-demo')
    parser.add_argument('--fail-once',action='store_true')
    parser.add_argument('--real-browser',action='store_true')
    parser.add_argument('--browser',choices=['chrome','edge','firefox'],default='edge')
    raise SystemExit(asyncio.run(demo(parser.parse_args())))
