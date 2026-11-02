"""Independent blinded human visual evaluation; never infer quality from HTML validity."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import shutil
import statistics

CRITERIA = ('readability','layout','overflow','profile_fidelity')


def export_review(report_path,output):
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    if report['browser']=='mock':
        raise ValueError('Simulated PNGs cannot be used as visual quality evidence')
    output = Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    cases=report.get('cases') or json.loads(Path(__file__).with_name('fixtures.json').read_text(encoding='utf-8'))
    expected_inputs=report['methodology']['paired_input_sha256']
    selected=[]
    for case in cases:
        if case['case_id'] not in expected_inputs:
            continue
        digest=hashlib.sha256(json.dumps(case,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if digest!=expected_inputs[case['case_id']]:
            raise ValueError('Visual review inputs do not match the benchmark input hashes')
        selected.append(case)
    if len(selected)!=len(expected_inputs):
        raise ValueError('Missing visual review inputs')
    (output/'cases.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
    candidates,labels = [],{}
    for run in report['primary_runs']:
        for snapshot in run['snapshots']:
            if not snapshot.get('screenshot'):
                continue
            source=Path(snapshot['screenshot'])
            if not source.is_file():
                raise ValueError('Missing screenshot')
            key=hashlib.sha256((run['run_id']+snapshot['page_id']).encode()).hexdigest()[:20]
            shutil.copyfile(source,output/f'{key}.png')
            candidates.append({'candidate_id':key,'screenshot':f'{key}.png','case_id':run['case_id'],
                               'page':snapshot['html_name'],'page_requirements':snapshot['description'],
                               'input_sha256':run['input_sha256']})
            labels[key]={'variant':run['variant'],'run_id':run['run_id'],'page_id':snapshot['page_id']}
    random.Random(0).shuffle(candidates)
    rubric={'readability':'1: unreadable text; 3: readable with noticeable hierarchy/contrast issues; 5: clear text and consistent hierarchy.',
            'layout':'1: severe overlap or disorder; 3: usable with alignment/spacing problems; 5: clear hierarchy, alignment and spacing at the captured viewport.',
            'overflow':'1: major clipping or hidden content; 3: minor clipping/scroll issues; 5: no visible clipping or overlap.',
            'profile_fidelity':'Compare with cases.json. 1: major omissions/invented facts; 3: some missing or inaccurate information; 5: complete, accurate profile content.'}
    manifest={'schema_version':1,'source_report_sha256':hashlib.sha256(Path(report_path).read_bytes()).hexdigest(),
              'rubric':rubric,'cases_file':'cases.json',
              'candidates':candidates,'notice':'Do not provide labels.json to reviewers. Scores must come from actual screenshot review.'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'labels.json').write_text(json.dumps(labels,indent=2),encoding='utf-8')
    ratings={'reviewer_id':'','ratings':[{'candidate_id':item['candidate_id'],**{key:None for key in CRITERIA}} for item in candidates]}
    (output/'ratings-template.json').write_text(json.dumps(ratings,indent=2),encoding='utf-8')
    return manifest


def score_review(manifest_path,labels_path,ratings_path):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    labels=json.loads(Path(labels_path).read_text(encoding='utf-8'))
    ratings=json.loads(Path(ratings_path).read_text(encoding='utf-8'))
    if not isinstance(ratings.get('reviewer_id'),str) or not ratings['reviewer_id'].strip():
        raise ValueError('A reviewer identifier is required')
    expected={item['candidate_id'] for item in manifest['candidates']}
    seen=set(); groups=defaultdict(list)
    for row in ratings.get('ratings',[]):
        key=row.get('candidate_id')
        if key not in expected or key in seen or key not in labels:
            raise ValueError('Unknown or duplicate candidate')
        if any(type(row.get(criterion)) is not int or not 1<=row[criterion]<=5 for criterion in CRITERIA):
            raise ValueError('All visual rubric scores must be integers from 1 to 5')
        seen.add(key)
        groups[labels[key]['variant']].append(row)
    if seen!=expected or not seen:
        raise ValueError('Every candidate must receive a real review')
    return {'method':'blinded_human_screenshot_rubric','reviewer_id':ratings['reviewer_id'],
            'source_report_sha256':manifest['source_report_sha256'],
            'variants':{variant:{'pages_reviewed':len(rows),
                                  **{criterion:statistics.mean(row[criterion] for row in rows) for criterion in CRITERIA},
                                  'mean_score':statistics.mean(row[c] for row in rows for c in CRITERIA)} for variant,rows in groups.items()}}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    commands=parser.add_subparsers(dest='command',required=True)
    export=commands.add_parser('export');export.add_argument('report');export.add_argument('--output',required=True)
    score=commands.add_parser('score');score.add_argument('--manifest',required=True);score.add_argument('--labels',required=True);score.add_argument('--ratings',required=True);score.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='export':
        result=export_review(args.report,args.output)
        print(json.dumps({'candidates':len(result['candidates']),'scores':'not_evaluated'}))
    else:
        result=score_review(args.manifest,args.labels,args.ratings)
        Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
