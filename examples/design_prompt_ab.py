"""Opt-in paid A/B experiment: real Runtime, provider, Selenium, and checkpoints.

The baseline directory must contain the prompts preserved before design-v2.
No API request occurs without --live. DOM indicators are not visual-quality scores.
"""
import argparse
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.budget import BudgetLimits
from harness.runtime import Runtime
from resumeagent.main import HomepageDesignAgent
from resumeagent.tools.browser import Webserver

PROFILE = {
    'basic_information': '张三，人工智能方向硕士研究生。',
    'academic_achievements': '研究方向：大语言模型、智能体系统、自动化决策。',
    'experience': '个人主页生成系统、多智能体执行框架。',
    'professional_skills': 'Python、PyTorch、Transformer、RAG、Agent、Selenium、HTML、CSS。',
}
FEEDBACK = '中文个人主页，现代、简洁、专业；只展示提供的事实。'
PLAN = [
    {'html_name':'index.html', 'is_main_page':True,
     'description':'张三，人工智能方向硕士研究生。研究方向：大语言模型、智能体系统、自动化决策。专业技能：Python、PyTorch、Transformer、RAG、Agent、Selenium、HTML、CSS。项目：个人主页生成系统、多智能体执行框架。',
     'page_style':'统一的中文研究者主页；清晰、专业的字体与导航；内容决定布局。',
     'relationship':{'buttons':[], 'links':[{'link_name':'首页','jump_page':'index.html'}, {'link_name':'项目','jump_page':'projects.html'}]},
     'js_description':'', 'practice_features':'响应式阅读和导航', 'additional_features':''},
    {'html_name':'projects.html', 'is_main_page':False,
     'description':'张三的项目：个人主页生成系统、多智能体执行框架。只知道项目名称，没有项目年份、技术实现或量化成果。',
     'page_style':'与首页共享配色、字体和导航；按项目内容设计构图。',
     'relationship':{'buttons':[], 'links':[{'link_name':'首页','jump_page':'index.html'}, {'link_name':'项目','jump_page':'projects.html'}]},
     'js_description':'', 'practice_features':'响应式阅读和导航', 'additional_features':''},
]


class CaptureBrowser(Webserver):
    """Archive actual first-render artifacts; generation still uses registered tools."""
    def __init__(self, directory):
        super().__init__(str(directory), web_type='edge')
        self.initial = Path(directory)/'initial'
        self.initial.mkdir(exist_ok=True)
        self.captured = {path.name for path in self.initial.glob('*.html')}

    def get_screenshot(self, local_html_path, save_path=None, is_local=True):
        result = super().get_screenshot(local_html_path, save_path, is_local)
        source = Path(local_html_path)
        if source.name not in self.captured:
            shutil.copy2(source, self.initial/source.name)
            for css in source.parent.glob('*.css'):
                shutil.copy2(css, self.initial/css.name)
            shutil.copy2(result, self.initial/(source.stem+'.png'))
            self.captured.add(source.name)
        return result


def baseline_modules(directory):
    spec = importlib.util.spec_from_file_location('resumeagent_baseline_prompts', directory/'__init__.py',
                                                submodule_search_locations=[str(directory)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return {name:importlib.import_module(f'{spec.name}.{name}') for name in ('generator','refiner')}


def preview_checks(browser, directory):
    results = []
    for path in sorted(directory.glob('*.html')):
        for width in (1440, 390):
            driver = browser.driver
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width':width, 'height':1000, 'deviceScaleFactor':1, 'mobile':width<600})
            driver.get(path.resolve().as_uri())
            time.sleep(2)
            data = driver.execute_script('''
                const text=document.body.innerText;
                const all=[...document.querySelectorAll('body *')];
                const boxes=all.filter(e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();
                  return r.width>100&&r.height>40&&parseFloat(s.borderRadius)>=8&&
                    (s.boxShadow!=='none'||s.backgroundColor!=='rgba(0, 0, 0, 0)');});
                return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
                  title:document.title,lang:document.documentElement.lang,text,
                  h1:document.querySelectorAll('h1').length,roundedPanels:boxes.length,
                  percentageStrings:text.match(/\\d+(?:\\.\\d+)?\\s*%/g)||[],
                  brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.getAttribute('src')),
                  links:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')),
                  styles:{bg:getComputedStyle(document.body).backgroundColor,font:getComputedStyle(document.body).fontFamily},
                  tokens:{bg:getComputedStyle(document.documentElement).getPropertyValue('--bg'),ink:getComputedStyle(document.documentElement).getPropertyValue('--ink'),accent:getComputedStyle(document.documentElement).getPropertyValue('--accent')}};
            ''')
            from urllib.parse import urlsplit, unquote
            data['missingLocalLinks'] = [href for href in data['links'] if not urlsplit(href).scheme
                                        and urlsplit(href).path and not (path.parent/unquote(urlsplit(href).path)).is_file()]
            shot=directory/f'qa-{path.stem}-{width}.png'
            driver.save_screenshot(str(shot))
            results.append(dict(file=path.name, screenshot=str(shot), **data))
    return results


async def run_variant(name, output, baseline=None, resume=False):
    directory = output/name
    directory.mkdir(exist_ok=resume)
    browser = CaptureBrowser(directory)
    agent = HomepageDesignAgent(model='qwen3.8-flash', save_file=str(directory), browser=browser)
    agent.task.update(PROFILE)
    agent.language, agent.css_frame, agent.user_feedback = 'zh', 'Tailwind', FEEDBACK
    agent.gen_img = False
    runtime = Runtime(agent, storage_root=output/'runtime', limits=BudgetLimits(
        max_iterations=1, max_concurrency=2, max_cost=1, request_timeout=600,
        max_run_seconds=1800, max_retries=1))
    with ExitStack() as stack:
        if baseline:
            stack.enter_context(patch('resumeagent.agents.generator.get_write_original_website_prompt', baseline['generator'].get_write_original_website_prompt))
            stack.enter_context(patch('resumeagent.agents.refiner.get_refine_prompt', baseline['refiner'].get_refine_prompt))
            stack.enter_context(patch('resumeagent.agents.refiner.get_evaluation_prompt', baseline['refiner'].get_evaluation_prompt))
        run_id = None
        if resume:
            with runtime.state.db.connect() as conn:
                ids = [row['id'] for row in conn.execute('SELECT id FROM runs ORDER BY created_at DESC')]
            run_id = next((identity for identity in ids if runtime.state.get_run(identity)['files'].get('output_dir') == str(directory.resolve())), None)
        if run_id is None:
            run_id = runtime.create_run(pages=deepcopy(PLAN), output_dir=directory)
        print(json.dumps({'variant':name,'run_id':run_id,
                          'status':'resuming' if resume else 'created'}), flush=True)
        started=time.monotonic()
        try:
            result=await runtime.execute(run_id)
            await runtime.aclose()
            # aclose releases the managed rendering browser. A separate preview is read-only QA.
            qa_browser=Webserver(str(directory),web_type='edge')
            try:
                initial=await asyncio.to_thread(preview_checks,qa_browser,directory/'initial')
                final=await asyncio.to_thread(preview_checks,qa_browser,directory)
            finally:
                await asyncio.to_thread(qa_browser.stop)
            report={'variant':name,'run_id':run_id,'status':result['status'],'error':result['error'],
                    'usage':result['usage'],'elapsed_seconds':time.monotonic()-started,
                    'runtime_elapsed_seconds':result['elapsed'],
                    'pages':runtime.generation_status(run_id)['pages'],
                    'tasks':[{k:t.get(k) for k in ('id','stage','status','attempts','result','error')} for t in runtime.state.tasks(run_id)],
                    'initial':initial,'final':final}
        finally:
            await runtime.aclose()
    (directory/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'variant':name,'run_id':run_id,'status':report['status'],'usage':report['usage']},ensure_ascii=False),flush=True)
    return report


async def execute(args):
    output=args.output.resolve()
    if args.feedback_only:
        if not args.feedback or not (output/'design-v2'/'result.json').is_file():
            raise ValueError('Feedback-only requires an existing design-v2 result and --feedback')
        os.environ['TOKEN_LOG_FILE']=str(output/'feedback-provider-tokens.json')
        await feedback_refinement(output,args.feedback)
        return
    if output.exists() and not args.resume:
        raise ValueError('Use a fresh experiment directory; existing artifacts are never overwritten')
    output.mkdir(parents=True,exist_ok=args.resume)
    os.environ['TOKEN_LOG_FILE']=str(output/'provider-tokens.json')
    os.environ.setdefault('SE_CACHE_PATH',str(ROOT/'.selenium-cache'))
    os.environ.setdefault('SE_AVOID_STATS','true')
    baseline=baseline_modules(args.baseline_prompts.resolve())
    inputs={'profile':PROFILE,'feedback':FEEDBACK,'plan':PLAN,
            'model':'qwen3.8-flash','framework':'Tailwind','max_iterations':1}
    input_path=output/'input.json'
    if args.resume and input_path.exists():
        if json.loads(input_path.read_text(encoding='utf-8')) != inputs:
            raise ValueError('Cannot resume a comparison with changed inputs')
    else:
        input_path.write_text(json.dumps(inputs,ensure_ascii=False,indent=2),encoding='utf-8')
    reports=[]
    for name,old in (('baseline',baseline),('design-v2',None)):
        if args.only and name != args.only:
            continue
        reports.append(await run_variant(name,output,old,args.resume))
        (output/'results.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')


async def feedback_refinement(output, feedback):
    """Explicit user-feedback path, only for pages not already visually refined."""
    source=output/'design-v2'
    prior=json.loads((source/'result.json').read_text(encoding='utf-8'))
    if prior['status']!='completed' or any(page['iteration'] for page in prior['pages']):
        raise ValueError('Feedback comparison requires a completed, unrefined initial result')
    target=output/'design-v2-refined'
    target.mkdir()  # Never mutate a completed Run's artifacts or fingerprints.
    for suffix in ('*.html','*.css','*.png'):
        for path in source.glob(suffix):
            if not path.name.startswith('qa-'):
                shutil.copy2(path,target/path.name)
    shutil.copytree(ROOT/'resumeagent/prompts',target/'prompt-source',ignore=shutil.ignore_patterns('__pycache__'))
    (target/'feedback.txt').write_text(feedback,encoding='utf-8')
    reports=[]
    for page in PLAN:
        agent=HomepageDesignAgent(model='qwen3.8-flash',save_file=str(target),browser=Webserver(str(target),web_type='edge'))
        agent.task.update(PROFILE)
        agent.language,agent.css_frame,agent.user_feedback='zh','Tailwind',feedback
        agent.gen_img=False
        runtime=Runtime(agent,storage_root=output/'runtime',limits=BudgetLimits(max_iterations=1,request_timeout=600,max_cost=.5,max_retries=1))
        run_id=runtime.create_run(pages=deepcopy(PLAN),output_dir=target,
                                  action={'method':'refine','args':[deepcopy(page)]})
        print(json.dumps({'variant':'design-v2-refined','page':page['html_name'],'run_id':run_id,'status':'created'}),flush=True)
        try:
            result=await runtime.execute(run_id)
            reports.append({'run_id':run_id,'page':page['html_name'],'status':result['status'],'usage':result['usage'],'elapsed':result['elapsed']})
        finally:
            await runtime.aclose()
    browser=Webserver(str(target),web_type='edge')
    try:
        qa=await asyncio.to_thread(preview_checks,browser,target)
    finally:
        await asyncio.to_thread(browser.stop)
    (target/'result.json').write_text(json.dumps({'feedback_runs':reports,'preview':qa},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'variant':'design-v2-refined','runs':reports},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Authorize real provider requests and Selenium')
    parser.add_argument('--resume',action='store_true',help='Resume the same experiment through Runtime checkpoints')
    parser.add_argument('--only',choices=('baseline','design-v2'),help='Run only one arm, keeping the same fixed inputs')
    parser.add_argument('--feedback-only',action='store_true',help='Apply one explicit feedback refinement to the existing unrefined design-v2 arm')
    parser.add_argument('--feedback',help='Concrete observed defects; never biographical evidence')
    parser.add_argument('--baseline-prompts',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'test-artifacts'/('design-ab-'+datetime.now().strftime('%Y%m%d-%H%M%S')))
    args=parser.parse_args()
    if not args.live:
        parser.error('Real A/B generation requires --live; this experiment uses paid API calls')
    asyncio.run(execute(args))


if __name__=='__main__':
    main()
