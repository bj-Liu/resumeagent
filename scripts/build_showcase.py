"""Validate and stage a dependency-light, self-contained GitHub Pages artifact."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def validate(folder, node='node'):
    import html5lib
    import tinycss2
    errors = []
    files = [p for p in folder.rglob('*') if p.is_file()]
    for file in files:
        relative = file.relative_to(folder)
        if file.suffix == '.html':
            parser = html5lib.HTMLParser(strict=False)
            document = parser.parse(file.read_text(encoding='utf-8'))
            errors.extend(f'{relative}: HTML {position}: {code}' for position, code, _ in parser.errors)
            ids = [e.attrib['id'] for e in document.iter() if 'id' in e.attrib]
            if len(ids) != len(set(ids)):
                errors.append(f'{relative}: duplicate element IDs')
            for element in document.iter():
                for attr in ('src', 'href', 'poster'):
                    raw = element.attrib.get(attr, '')
                    url = urlsplit(raw)
                    if not raw or url.scheme or url.netloc:
                        continue
                    if url.path.startswith('/'):
                        errors.append(f'{relative}: root-relative URL breaks project Pages: {raw}')
                        continue
                    target = (file.parent / unquote(url.path)).resolve() if url.path else file.resolve()
                    if not target.is_relative_to(folder.resolve()) or not target.is_file():
                        errors.append(f'{relative}: missing or unconfined resource: {raw}')
                    elif url.fragment and target.suffix == '.html':
                        target_doc = parser.parse(target.read_text(encoding='utf-8'))
                        if not any(e.attrib.get('id') == url.fragment for e in target_doc.iter()):
                            errors.append(f'{relative}: missing HTML anchor: {raw}')
        elif file.suffix == '.css':
            def inspect_rules(rules):
                for rule in rules:
                    if rule.type == 'error':
                        errors.append(f'{relative}: CSS {rule.source_line}: {rule.message}')
                    if rule.type == 'qualified-rule':
                        for declaration in tinycss2.parse_declaration_list(rule.content, skip_comments=True, skip_whitespace=True):
                            if declaration.type == 'error':
                                errors.append(f'{relative}: CSS declaration: {declaration.message}')
                    elif rule.type == 'at-rule' and rule.content and rule.lower_at_keyword in ('media', 'supports', 'layer'):
                        inspect_rules(tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True))
            text = file.read_text(encoding='utf-8')
            inspect_rules(tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True))
            for raw in re.findall(r'url\([\s\'"]*([^\)\'"\s]+)', text):
                if not urlsplit(raw).scheme and not (file.parent / unquote(raw)).is_file():
                    errors.append(f'{relative}: missing CSS resource: {raw}')
        elif file.suffix == '.js':
            result = subprocess.run([node, '--check', str(file)], capture_output=True, text=True)
            if result.returncode:
                errors.append(f'{relative}: JavaScript syntax check failed: {result.stderr}')
        elif file.suffix == '.json':
            json.loads(file.read_text(encoding='utf-8'))
        elif file.suffix == '.svg':
            ElementTree.parse(file)
    evidence = json.loads((folder / 'data/evidence.json').read_text(encoding='utf-8'))
    tests = evidence['tests']
    if tests['passed'] + tests['skipped'] + tests['failures'] != tests['total']:
        errors.append('Inconsistent test evidence counters')
    if errors:
        raise ValueError('\n'.join(errors))
    return len(files)


def build(output, node='node'):
    output = Path(output).resolve()
    permitted_root = (ROOT / 'release-dist').resolve()
    if not output.is_relative_to(permitted_root) or output == permitted_root:
        raise ValueError('Build output must be a child of release-dist; source files are never deleted')
    if output.exists():
        # Only this previously verified build child is replaced; never the source tree.
        shutil.rmtree(output)
    shutil.copytree(ROOT / 'showcase', output)
    docs = output / 'docs'
    docs.mkdir(exist_ok=True)
    for filename in ('architecture.md', 'architecture.mmd', 'architecture.svg', 'DEMO_SCRIPT.md', 'RELEASE_CHECKS.md'):
        shutil.copy2(ROOT / 'docs' / filename, docs / filename)
    for filename in ('README.md', 'LICENSE'):
        shutil.copy2(ROOT / filename, docs / filename)
    (output / '.nojekyll').touch()
    count = validate(output, node)
    print(f'Validated {count} static files: HTML, CSS, JavaScript, SVG, JSON and local asset paths. Output: {output}')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='release-dist/showcase')
    parser.add_argument('--node', default=os.environ.get('NODE_BINARY', 'node'))
    args = parser.parse_args()
    try:
        build(args.output, args.node)
    except (ValueError, OSError, ImportError) as error:
        print(f'Showcase build refused: {error}', file=sys.stderr)
        raise SystemExit(1)
