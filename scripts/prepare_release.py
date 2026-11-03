"""Create a source-only release candidate and audit it without publishing private data."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('resumeagent','harness','storage','mcp','evals','examples','tests','gui_assets','showcase','scripts','.github')
ROOT_FILES = ('main.py','README.md','LICENSE','requirements.txt','requirements-showcase.txt',
              '.gitignore','.env.example','config.example.yaml')
DOC_FILES = ('architecture.md','architecture.mmd','architecture.svg','DEMO_SCRIPT.md',
             'DEMO_PROFILE.md','DEMO_VIDEO.json','LIVE_DEMO.md','RELEASE_CHECKS.md','benchmark.md','benchmark.json','RELEASE_GUIDE.md','SOURCE_MAP.md','SECURITY_AUDIT.md')
ALLOWED_SUFFIXES = {'.py','.json','.png','.svg','.html','.css','.js','.md','.yaml','.yml','.txt'}
PRIVATE_NAMES = {'config.yaml','.env','se-metadata.json'}
PRIVATE_PARTS = {'__pycache__','runs','outputs','mcp','.pytest_cache'}


def candidate_files(root=ROOT):
    """Explicit selection: expanding this list is a reviewable release decision."""
    files = [root/name for name in ROOT_FILES if (root/name).is_file()]
    files.extend(root/'docs'/name for name in DOC_FILES if (root/'docs'/name).is_file())
    for name in DIRECTORIES:
        folder = root/name
        if not folder.exists():
            continue
        for path in folder.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(folder)
            if path.name in PRIVATE_NAMES or '__pycache__' in relative.parts:
                continue
            if name == 'storage' and relative.parts[0] in ('runs','outputs','mcp'):
                continue
            if path.suffix not in ALLOWED_SUFFIXES:
                continue
            files.append(path)
    return sorted(set(files),key=lambda p:p.relative_to(root).as_posix())


def known_credentials(root):
    import yaml
    values = set()
    for path in (root/'config.yaml',root/'resumeagent/config.yaml'):
        if path.exists():
            mapping = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
            for key,value in mapping.items():
                if re.search(r'(api.?key|secret|password|azure_openai_key)',key,re.I) and isinstance(value,str) and len(value)>8:
                    values.add(value)
    return values


def inspect(files, root=ROOT):
    secrets = known_credentials(root)
    issues=[]
    records=[]
    for path in files:
        data=path.read_bytes()
        name=path.relative_to(root).as_posix()
        if any(value.encode() in data for value in secrets):
            issues.append({'path':name,'kind':'matches local credential value'})
        if path.suffix not in ('.png',):
            text=data.decode('utf-8')
            if re.search(r'(?<![\w-])(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',text):
                issues.append({'path':name,'kind':'credential-shaped string'})
        records.append({'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                        'git_blob_sha1':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    return records,issues


def prepare(root=ROOT):
    output=root/'release-dist'
    output.mkdir(exist_ok=True)
    files=candidate_files(root)
    records,issues=inspect(files,root)
    audit={'files':len(records),'bytes':sum(r['size'] for r in records),'secret_findings':issues,
           'method':'Explicit source allowlist; exact local credential matches + credential-shaped strings. No scan can guarantee absence of all personal data.',
           'excluded':'Local credential YAML, env files, profiles, runtime stores, outputs, logs, caches, test artifacts, private backup and unreviewed historical reports/media.'}
    (output/'security-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    if issues:
        raise ValueError('Source archive refused: review security-audit.json (values are never printed)')
    (output/'source-manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    target=output/'resumeagent-source.zip'
    with ZipFile(target,'w',compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path,path.relative_to(root).as_posix())
        for directory in ('storage/runs/.gitkeep','storage/outputs/.gitkeep'):
            archive.writestr(directory,b'')
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    (output/'resumeagent-source.zip.sha256').write_text(f'{checksum}  {target.name}\n',encoding='utf-8')
    print(json.dumps({'archive':str(target),'source_files':len(records),'archive_bytes':target.stat().st_size,'sha256':checksum,'secret_findings':len(issues)}))


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
