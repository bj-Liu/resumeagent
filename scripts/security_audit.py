"""Redacted credential scan of a workspace, proposed source and all reachable Git blobs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile

from prepare_release import ROOT, candidate_files, known_credentials

PATTERNS = [
    ('provider_token', re.compile(rb'(?<![\w-])(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})')),
    ('aws_access_key', re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('google_api_key', re.compile(rb'\bAIza[0-9A-Za-z_-]{35}\b')),
    ('slack_token', re.compile(rb'\bxox[baprs]-[0-9A-Za-z-]{20,}\b')),
    ('private_key', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
]
ASSIGNMENT = re.compile(rb'''(?i)(?:[\w-]*(?:api[_-]?key|secret|password|access[_-]?token|auth[_-]?token)[\w-]*|\btoken\b)["']?[ \t]*[:=][ \t]*["']?([a-zA-Z0-9_./+\-=]{16,})["']?[ \t]*(?=[,}\r\n]|$)''')


def kinds(data, credentials):
    found={name for name,pattern in PATTERNS if pattern.search(data)}
    if any(value.encode() in data for value in credentials):
        found.add('exact_local_credential')
    for match in ASSIGNMENT.finditer(data):
        value=match[1]
        if any(word in value.lower() for word in (b'fixture',b'example',b'test',b'dummy',b'placeholder',b'your',b'os.environ',b'process.env')):
            continue
        entropy=-sum((value.count(c)/len(value))*math.log2(value.count(c)/len(value)) for c in set(value))
        if entropy>3.5:
            found.add('high_entropy_credential_assignment')
    return sorted(found)


def git(repo, executable, *args):
    command=[executable,'-c',f'safe.directory={repo.as_posix()}','-C',str(repo),*args]
    return subprocess.check_output(command,stderr=subprocess.PIPE)


def audit(repo, executable, output):
    credentials=known_credentials(ROOT)
    proposed=candidate_files()
    candidate_findings=[{'path':p.relative_to(ROOT).as_posix(),'kinds':found} for p in proposed if (found:=kinds(p.read_bytes(),credentials))]
    # Read local private files too, but do not scan caches, screenshots/video bytes,
    # browser downloads, duplicate test stores or the GitHub CLI credential store.
    workspace_findings=[]
    reviewed=0
    excluded={'.release-work','.release-backups','.selenium-cache','__pycache__','.git'}
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in excluded for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() not in ('.py','.yaml','.yml','.json','.md','.txt','.env','.html','.css','.js','.log') and path.name!='.env':
            continue
        if path.stat().st_size>15_000_000:
            continue
        reviewed+=1
        found=kinds(path.read_bytes(),credentials)
        if found:
            workspace_findings.append({'path':path.relative_to(ROOT).as_posix(),'kinds':found,
                                       'included_in_source':path in proposed})
    tracked=git(repo,executable,'ls-files','-z').split(b'\0')
    tracked_findings=[]
    for raw in tracked:
        if raw:
            name=raw.decode('utf-8')
            path=repo/name
            if path.is_file() and (found:=kinds(path.read_bytes(),credentials)):
                tracked_findings.append({'path':name,'kinds':found})
    objects=git(repo,executable,'rev-list','--objects','--all').decode('utf-8').splitlines()
    history_findings=[]
    blobs=0
    metadata_objects=0
    for line in objects:
        sha,_,name=line.partition(' ')
        objtype=git(repo,executable,'cat-file','-t',sha).strip()
        if objtype not in (b'blob',b'commit',b'tag'):
            continue
        if objtype==b'blob':
            blobs+=1
        else:
            metadata_objects+=1
        data=git(repo,executable,'cat-file',objtype.decode(),sha)
        found=kinds(data,credentials)
        if found:
            commits=git(repo,executable,'log','--all','--format=%H',f'--find-object={sha}').decode().splitlines()
            history_findings.append({'object':sha,'object_type':objtype.decode(),'path_hint':name,'kinds':found,'commits':commits})
    report={'scope':{'head':git(repo,executable,'rev-parse','HEAD').decode().strip(),'workspace_text_files':reviewed,'proposed_files':len(proposed),'tracked_files':len([p for p in tracked if p]),
                     'reachable_commits':int(git(repo,executable,'rev-list','--count','--all')),'reachable_blobs':blobs,'metadata_objects':metadata_objects,
                     'remote_main':git(repo,executable,'rev-parse','origin/main').decode().strip()},
            'workspace_findings':workspace_findings,'candidate_findings':candidate_findings,
            'tracked_findings':tracked_findings,'history_findings':history_findings,
            'limitations':['Pattern and exact-value scanning cannot prove absence of every unknown credential.',
                           'Binary media require separate visual review; no claim of OCR coverage.',
                           'Unreachable objects, deleted upstream refs and credentials in provider systems are outside this scan.'],
            'safe_to_publish_scanned_candidate':not candidate_findings and not history_findings and not tracked_findings}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scope':report['scope'],'candidate_findings':len(candidate_findings),
                      'tracked_findings':len(tracked_findings),'history_findings':len(history_findings),
                      'workspace_findings':len(workspace_findings),'report':str(output)}))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--git',default='git')
    parser.add_argument('--output',default='test-artifacts/release/security-audit.json',type=Path)
    args=parser.parse_args()
    report=audit(args.repo.resolve(),args.git,args.output)
    if not report['safe_to_publish_scanned_candidate']:
        raise SystemExit(1)
