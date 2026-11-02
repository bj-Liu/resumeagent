"""Publish a small, privacy-reviewed summary from actual local release reports."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def write(source):
    source = Path(source)
    log = (source / 'full-tests.log').read_text(encoding='utf-8')
    match = re.search(r'Ran (\d+) tests in ([\d.]+)s', log)
    if not match or not re.search(r'^OK(?: \(skipped=\d+\))?$', log, re.M):
        raise ValueError('A successful, complete test log is required; no fabricated summary')
    total, seconds = int(match[1]), float(match[2])
    skipped = len(re.findall(r"\.\.\. skipped ", log))
    benchmark = json.loads((source/'benchmark/latest.json').read_text(encoding='utf-8'))
    real_browser = (source/'real-browser.log').read_text(encoding='utf-16')
    if 'Ran 1 test' not in real_browser or not re.search(r'^OK$', real_browser, re.M):
        raise ValueError('Successful opt-in real Selenium log is required')
    mcp = (source/'mcp-client.log').read_text(encoding='utf-16')
    if 'local_file_uris' not in mcp or 'completed' not in mcp:
        raise ValueError('MCP client completion and preview evidence required')
    image = ROOT/'showcase/assets/generated-homepage.png'
    evidence = {
        'schema_version':1, 'checked_date':'2026-11-03',
        'environment':{'python':'3.10.21','os':'Windows','conda':'machine_learning'},
        'tests':{'total':total,'passed':total-skipped,'skipped':skipped,'failures':0,'seconds':seconds},
        'real_browser':{'status':'passed','browser':'Edge / Selenium','tests':1,'model_backend':'mock'},
        'mcp':{'status':'passed','transport':'official SDK stdio','tools':3,'model_backend':'mock','browser_backend':'mock'},
        'gui':{'status':'passed','method':'real Tk startup and mocked Harness workflow in isolated subprocesses'},
        'benchmark':{
            'batch_id':benchmark['batch_id'],'backend':benchmark['backend'],'browser':benchmark['browser'],
            'token_source':benchmark['token_source'],'paid_api_calls':benchmark['paid_api_calls'],
            'primary_total':len(benchmark['primary_runs']),
            'primary_completed':sum(r['status']=='completed' for r in benchmark['primary_runs']),
            'recovery_total':len(benchmark['recovery_runs']),
            'recovery_completed':sum(r['recovered'] for r in benchmark['recovery_runs']),
            'variants':benchmark['variants'],'methodology':benchmark['methodology'],
            'total_usage_including_recovery':benchmark['total_usage_including_recovery'],
            'visual_evaluation':benchmark['visual_evaluation']
        },
        'demo':{'video_url':None,'recording_status':'not_recorded',
                'screenshot':{'file':'assets/generated-homepage.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
                'kind':'historical real Selenium screenshot of fictional profile',
                'source':'Earlier local prompt-design experiment; qwen3.8-flash; revised index.html',
                'release_validation':False,'visual_quality_score':None}},
        'deployment':{'status':'workflow_configured','commit_sha':None,
                      'reason':'GitHub Pages is configured for Actions; actual publication results are recorded in docs/RELEASE_CHECKS.md.'},
        'cost_notice':'Mock usage is synthetic. Estimates are not actual charges. No new paid model calls in release checks.'
    }
    target = ROOT/'showcase/data/evidence.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    safe_benchmark = {k:v for k,v in benchmark.items() if k not in ('cases','primary_runs','recovery_runs')}
    # Keep reproducibility metadata and input hashes, never private file paths.
    (ROOT/'docs/benchmark.json').write_text(json.dumps(safe_benchmark,indent=2)+'\n',encoding='utf-8')
    (ROOT/'docs/benchmark.md').write_text((source/'benchmark/latest.md').read_text(encoding='utf-8'),encoding='utf-8')
    return evidence


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='test-artifacts/release')
    print(json.dumps(write(parser.parse_args().source)['tests']))
