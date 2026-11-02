"""Deterministic offline boundaries. All usage here is declared synthetic fixture usage."""
import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw
from harness.context import CURRENT_EXECUTION
from harness.runtime import Runtime
from resumeagent.main import HomepageDesignAgent
from resumeagent.llm.client import record_tokens


def load_cases():
    return json.loads(Path(__file__).with_name('fixtures.json').read_text(encoding='utf-8'))


def page_specs(case):
    return [dict(page,css_name=page['html_name'].replace('.html','.css'),is_main_page=i==0,
                 relationship={'buttons':[],'links':[{'link_name':'Home','jump_page':'index.html'}]},
                 page_style='Readable, responsive blue and white cards') for i,page in enumerate(case['pages'])]


@dataclass
class Faults:
    api_failures: int = 0
    page_failures: int = 0
    render_failures: int = 0


class FixtureLLM:
    """Not a real model: 100 input/40 output fixture tokens per successful response."""
    def __init__(self, case, faults=None, delay=.005):
        self.case = deepcopy(case)
        self.faults = faults or Faults()
        self.delay = delay
        self.calls = Counter()
        self.active = self.peak = 0

    async def response_async(self,messages,**kwargs):
        self.active += 1
        self.peak = max(self.peak,self.active)
        try:
            await asyncio.sleep(self.delay)
            scope = CURRENT_EXECUTION.get()
            runtime = scope.runtime
            page = runtime.state.page(scope.page_id) if scope.page_id else None
            name = page['spec']['html_name'] if page else ''
            self.calls[(scope.stage,name)] += 1
            if scope.stage == 'generation' and name == self.case['pages'][0]['html_name'] and self.faults.api_failures:
                self.faults.api_failures -= 1
                raise ConnectionError('Fixture provider failure; no real API call')
            record_tokens(kwargs.get('model','fixture-model'),100,40)
            if scope.stage == 'planning':
                specs = page_specs(self.case)
                text = messages[-1]['content'][-1]['text']
                if '<modified_page>' in text:
                    spec = next(p for p in specs if f"'html_name': '{p['html_name']}'" in text)
                    return '<modified_page>'+json.dumps(spec,ensure_ascii=False)+'</modified_page>'
                return '<designed_pages>'+json.dumps(specs,ensure_ascii=False)+'</designed_pages>'
            if scope.stage == 'evaluation':
                return '<evaluation>'+json.dumps({'needs_refinement':page['iteration']<1,'feedback':'Increase spacing and maintain readable navigation.'})+'</evaluation>'
            if scope.stage == 'generation' and name == self.case['pages'][0]['html_name'] and self.faults.page_failures:
                self.faults.page_failures -= 1
                return 'Fixture malformed output, intentionally missing HTML fences.'
            title = html.escape(page['spec']['description'])
            profile = runtime.context.profile
            content = ''.join(f'<p>{html.escape(str(value or ""))}</p>' for value in profile.values())
            navigation = ''.join(f'<a href="{p["html_name"]}">{html.escape(p["description"])}</a> ' for p in self.case['pages'])
            css = 'body{font:18px system-ui;margin:40px;color:#16304c;background:#eff6ff}main{background:white;padding:32px;border-radius:16px}nav{margin-bottom:32px}a{margin-right:18px}p{white-space:pre-wrap}'
            document = f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{css}</style></head><body><nav>{navigation}</nav><main><h1>{title}</h1>{content}</main></body></html>'
            return '```html\n'+document+'\n```\n```css\n'+css+'\n```'
        finally:
            self.active -= 1


class FixtureBrowser:
    """Valid PNG test double, not an HTML renderer or visual quality evaluator."""
    def __init__(self,faults=None):
        self.faults = faults or Faults()
        self.calls = Counter()

    def get_screenshot(self,html_path,save_path):
        if not Path(html_path).is_file():
            raise FileNotFoundError(html_path)
        self.calls[Path(html_path).name] += 1
        if self.faults.render_failures and Path(html_path).name == 'index.html':
            self.faults.render_failures -= 1
            raise RuntimeError('Fixture browser failure')
        image = Image.new('RGB',(800,450),'#eff6ff')
        ImageDraw.Draw(image).text((30,30),'SIMULATED PNG - not an HTML render',fill='#16304c')
        Path(save_path).parent.mkdir(parents=True,exist_ok=True)
        image.save(save_path)

    def open_website(self,path):
        pass

    def stop(self):
        pass


def runtime_factory(root,case=None,*,limits=None,faults=None,browser='mock',delay=.005):
    case = case or load_cases()[0]
    faults = faults or Faults()
    backend = FixtureLLM(case,faults,delay)
    if browser == 'mock':
        renderer = FixtureBrowser(faults)
    else:
        from resumeagent.tools.browser import Webserver
        renderer = Webserver(str(Path(root)/'outputs'),web_type=browser)
    agent = HomepageDesignAgent(model='fixture-model',save_file=str(Path(root)/'outputs'),llm=backend,browser=renderer)
    agent.execution_mode = 'mock'
    agent.rendering_mode = 'mock' if browser == 'mock' else 'selenium'
    agent.gen_img = False
    agent.language = case.get('language','en')
    return Runtime(agent,storage_root=root,limits=limits)
