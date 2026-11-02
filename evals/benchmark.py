"""Measured, paired Harness benchmark. Mock results are never labeled real model quality/billing."""
import argparse
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
from urllib.parse import urlparse, unquote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup, Doctype
from harness.budget import BudgetLimits
from harness.runtime import Runtime
from evals.support import Faults, load_cases, page_specs, runtime_factory
from resumeagent.llm import client


def input_digest(case):
    return hashlib.sha256(json.dumps(case,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_html(path, output_root):
    """Independent artifact check; deliberately not a visual quality score."""
    path, root = Path(path), Path(output_root).resolve()
    if not path.is_file() or not path.resolve().is_relative_to(root):
        return False
    soup = BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
    if not all(soup.find(tag) for tag in ('html','head','title','body')):
        return False
    if not any(isinstance(node,Doctype) for node in soup.contents):
        return False
    for link in soup.find_all(['a','link','img','script']):
        target = link.get('href') if link.name in ('a','link') else link.get('src')
        if not target or target.startswith('#'):
            continue
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            continue
        filename = unquote(parsed.path)
        if not filename:
            continue
        resolved = (path.parent/filename).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return False
    return True


def collect_run(runtime,run_id,case,variant,wall_seconds,*,backend,browser,repeat=0):
    run = runtime.state.get_run(run_id)
    pages = runtime.state.pages(run_id)
    tasks = runtime.state.tasks(run_id)
    expected = len(case['pages']) if backend == 'mock' else max(len(pages),len(run['context'].get('plan') or []))
    output = Path(run['files']['output_dir'])
    html_pass = sum(validate_html(page['files'].get('html',''),output) for page in pages)
    events = runtime.tracer.query(run_id)
    started = {e.get('request_id') for e in events if e['event']=='llm.started'}
    reported = {e.get('request_id') for e in events if e['event']=='llm.usage'}
    snapshots = [{'page_id':p['id'],'html_name':p['spec']['html_name'],'screenshot':p['files'].get('screenshot'),
                  'description':p['spec'].get('description','')} for p in pages if p['status']=='completed']
    return {'run_id':run_id,'case_id':case['case_id'],'input_sha256':input_digest(case),'variant':variant,'repeat':repeat,
            'model':run['context']['settings']['model'],
            'settings':{k:run['context']['settings'][k] for k in ('css_frame','language','vision','gen_img')},
            'status':run['status'],'wall_seconds':wall_seconds,'runtime_elapsed_seconds':run['elapsed'],
            'pages_expected':expected,'pages_completed':sum(p['status']=='completed' for p in pages),
            'pages_generated':len({t['page_id'] for t in tasks if t['stage']=='generation' and t['status']=='completed'}),
            'html_validation_passes':html_pass,
            'refinement_calls':sum(t['stage']=='refinement' and t['status']=='completed' for t in tasks),
            'prompt_tokens':run['usage'].get('prompt_tokens',0),'completion_tokens':run['usage'].get('completion_tokens',0),
            'api_cost_estimate':run['usage'].get('cost',0),'api_cost_actual':None,
            'usage_complete':not bool(started-reported),'unreported_requests':len(started-reported),
            'token_source':'synthetic_fixture_usage' if backend=='mock' else 'provider_reported_usage',
            'cost_source':'legacy_or_configured_estimate','browser':browser,'snapshots':snapshots}


def ratio(numerator,denominator):
    return numerator/denominator if denominator else None


def summarize(records,recoveries):
    expected = sum(r['pages_expected'] for r in records)
    return {'tasks_total':len(records),'task_success_rate':ratio(sum(r['status']=='completed' for r in records),len(records)),
            'pages_expected':expected,'page_generation_success_rate':ratio(sum(r['pages_generated'] for r in records),expected),
            'page_completion_rate':ratio(sum(r['pages_completed'] for r in records),expected),
            'average_execution_seconds':statistics.mean(r['wall_seconds'] for r in records) if records else None,
            'prompt_tokens':sum(r['prompt_tokens'] for r in records),'completion_tokens':sum(r['completion_tokens'] for r in records),
            'api_cost_estimate':sum(r['api_cost_estimate'] for r in records),'api_cost_actual':None,
            'average_iterations_per_expected_page':ratio(sum(r['refinement_calls'] for r in records),expected),
            'recovery_attempts':len(recoveries),'recovery_success_rate':ratio(sum(r['recovered'] for r in recoveries),len(recoveries)),
            'html_validation_pass_rate':ratio(sum(r['html_validation_passes'] for r in records),expected),
            'usage_complete':all(r.get('usage_complete',True) for r in records),
            'visual_quality_score':None}


def benchmark_markdown(report):
    def fmt(value,percent=False):
        if value is None:
            return 'not measured'
        return f'{value*100:.1f}%' if percent else f'{value:.3f}'
    lines = ['# Measured Harness benchmark', '',
             f"Batch: `{report['batch_id']}`; backend: `{report['backend']}`; browser: `{report['browser']}`.",
             f"Token source: `{report['token_source']}`. Costs are estimates, not actual bills.", '',
             '| Variant | Runs | Task success | Page generation | Avg seconds | Prompt tokens | Completion tokens | Estimated cost | Avg iterations/page | Recovery success | HTML pass |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for variant,stats in report['variants'].items():
        cells = [variant,str(stats['tasks_total']),fmt(stats['task_success_rate'],True),
                 fmt(stats['page_generation_success_rate'],True),fmt(stats['average_execution_seconds']),
                 str(stats['prompt_tokens']),str(stats['completion_tokens']),f"{stats['api_cost_estimate']:.6f}",
                 fmt(stats['average_iterations_per_expected_page']),fmt(stats['recovery_success_rate'],True),
                 fmt(stats['html_validation_pass_rate'],True)]
        lines.append('| '+' | '.join(cells)+' |')
    lines += ['', 'Primary statistics exclude separate recovery runs; see the JSON records for denominators, inputs, Run IDs and recovery usage.',
              'Visual quality: not evaluated. HTML validity and mock PNGs are not visual quality evidence.',
              'A single local repeat is a smoke benchmark, not evidence of model quality or statistically significant performance.']
    return '\n'.join(lines)+'\n'


@contextmanager
def isolated_token_log(path):
    original = client.token_log_file
    client.token_log_file = str(path)
    try:
        yield
    finally:
        client.token_log_file = original


async def run_benchmark(output,*,backend='mock',browser='mock',repeats=1,case_ids=None,variants=None,recovery=True,model=None,prices=None):
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    if backend not in ('mock','live') or repeats<1 or (backend=='live' and browser=='mock'):
        raise ValueError('Live evaluation requires a real browser; repeats must be positive')
    cases = [c for c in load_cases() if not case_ids or c['case_id'] in case_ids]
    if not cases:
        raise ValueError('No evaluation cases selected')
    variants = variants or {'baseline':0,'refined':2}
    batch = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    storage = output/'runs'/batch
    records, recoveries = [], []
    # Alternate execution order to avoid systematically giving one variant the warm browser/cache.
    with isolated_token_log(output/f'{batch}-tokens.json'):
        for repeat in range(repeats):
            for case_index,case in enumerate(cases):
                order = list(variants.items())
                if (case_index+repeat)%2:
                    order.reverse()
                for variant,iterations in order:
                    limits = BudgetLimits(max_cost=1,max_iterations=iterations,max_concurrency=2,max_retries=0,max_run_seconds=600,prices=prices)
                    if backend=='mock':
                        runtime = runtime_factory(storage,case,limits=limits,browser=browser)
                    else:
                        runtime = Runtime.configured(storage_root=storage,limits=limits,model=model,browser=browser)
                    try:
                        run_id = runtime.create_run(deepcopy(case['profile']),feedback=case.get('feedback',''),language=case.get('language','en'))
                        start = time.perf_counter()
                        await runtime.execute(run_id)
                        await runtime.aclose()
                        records.append(collect_run(runtime,run_id,case,variant,time.perf_counter()-start,backend=backend,browser=browser,repeat=repeat))
                    finally:
                        await runtime.aclose()
                    if recovery and backend=='mock':
                        faults = Faults(api_failures=1)
                        runtime = runtime_factory(storage,case,limits=limits,faults=faults,browser=browser)
                        try:
                            run_id = runtime.create_run(deepcopy(case['profile']),pages=page_specs(case),feedback=case.get('feedback',''),language=case.get('language','en'))
                            start = time.perf_counter()
                            first = await runtime.execute(run_id)
                            before = {p['id']:p['status'] for p in runtime.state.pages(run_id)}
                            completed_before = [p for p in runtime.state.pages(run_id) if p['status']=='completed']
                            calls_before = dict(runtime.agent.llm.calls)
                            final = await runtime.resume(run_id)
                            repeated = any(runtime.agent.llm.calls[('generation',p['spec']['html_name'])] != calls_before.get(('generation',p['spec']['html_name']),0) for p in completed_before)
                            recoveries.append({'run_id':run_id,'case_id':case['case_id'],'input_sha256':input_digest(case),
                                               'variant':variant,'repeat':repeat,'initial_status':first['status'],'final_status':final['status'],
                                               'recovered':first['status']=='failed' and final['status']=='completed' and not repeated,
                                               'completed_pages_regenerated':repeated,'pages_before_resume':before,
                                               'wall_seconds':time.perf_counter()-start,
                                               'prompt_tokens':final['usage'].get('prompt_tokens',0),'completion_tokens':final['usage'].get('completion_tokens',0),
                                               'api_cost_estimate':final['usage'].get('cost',0)})
                        finally:
                            await runtime.aclose()
    report = {'schema_version':1,'batch_id':batch,'created_at':datetime.now(timezone.utc).isoformat(),
              'python':platform.python_version(),'platform':platform.platform(),'backend':backend,'browser':browser,
              'cases':deepcopy(cases),
              'token_source':'synthetic_fixture_usage' if backend=='mock' else 'provider_reported_usage',
              'paid_api_calls':0 if backend=='mock' else None,
              'cost_notice':'Estimates from configured/legacy rates, not a provider invoice.',
              'methodology':{'paired_input_sha256':{c['case_id']:input_digest(c) for c in cases},
                             'repeats':repeats,'variants':variants,'order':'alternating by case and repeat',
                             'denominator':'Expected fixture pages for mock; actual planned pages for live. Live planning failures also count as task failures.',
                             'timing':'Wall time includes execute and background draining; Run creation excluded.',
                             'recovery_protocol':'Separate preplanned runs with one injected provider failure; excluded from primary task/page rates.',
                             'html_validation':'Independent document structure and local target existence; not visual quality.'},
              'variants':{variant:summarize([r for r in records if r['variant']==variant],[r for r in recoveries if r['variant']==variant]) for variant in variants},
              'primary_runs':records,'recovery_runs':recoveries,
              'total_usage_including_recovery':{'prompt_tokens':sum(r['prompt_tokens'] for r in records+recoveries),
                                                'completion_tokens':sum(r['completion_tokens'] for r in records+recoveries),
                                                'api_cost_estimate':sum(r['api_cost_estimate'] for r in records+recoveries)},
              'visual_evaluation':{'status':'not_evaluated','method':'independent blinded human screenshot rubric',
                                   'eligible':browser!='mock','score':None}}
    path = output/f'benchmark-{batch}.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'latest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    path.with_suffix('.md').write_text(benchmark_markdown(report),encoding='utf-8')
    (output/'latest.md').write_text(benchmark_markdown(report),encoding='utf-8')
    return report,path


async def main(args):
    report,path = await run_benchmark(args.output,backend=args.backend,browser=args.browser,repeats=args.repeats,
                                    case_ids=args.case,recovery=not args.skip_recovery,model=args.model,
                                    prices=json.loads(Path(args.prices_json).read_text(encoding='utf-8')) if args.prices_json else None)
    print(json.dumps({'report':str(path),'backend':report['backend'],'browser':report['browser'],
                      'token_source':report['token_source'],'variants':report['variants']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='test-artifacts/benchmark')
    parser.add_argument('--backend',choices=['mock','live'],default='mock')
    parser.add_argument('--browser',choices=['mock','edge','chrome','firefox'],default='mock')
    parser.add_argument('--model')
    parser.add_argument('--prices-json',help='Optional model to [input,output] rates per million tokens, in a consistent currency')
    parser.add_argument('--repeats',type=int,default=1)
    parser.add_argument('--case',action='append')
    parser.add_argument('--skip-recovery',action='store_true')
    asyncio.run(main(parser.parse_args()))
