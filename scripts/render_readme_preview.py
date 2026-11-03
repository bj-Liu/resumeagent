"""Render the actual README for local visual review; never serve private files."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]


def render(folder):
    folder = Path(folder).resolve()
    if not folder.is_relative_to(ROOT / 'release-dist') or not folder.is_dir():
        raise ValueError('Use an existing isolated release-dist build')
    markdown = MarkdownIt('commonmark').enable('table')
    tokens = markdown.parse((ROOT / 'README.md').read_text(encoding='utf-8'))

    def rewrite(items):
        for item in items:
            attribute = 'src' if item.type == 'image' else 'href'
            value = item.attrGet(attribute)
            if value and not urlsplit(value).scheme:
                if value.startswith('showcase/'):
                    item.attrSet(attribute, value.removeprefix('showcase/'))
                elif attribute == 'href' and value.startswith('docs/'):
                    item.attrSet(attribute, 'https://github.com/bj-Liu/resumeagent/blob/main/' + value)
            elif value == 'https://bj-liu.github.io/resumeagent/#results':
                item.attrSet(attribute, 'index.html#results')
            if item.children:
                rewrite(item.children)

    rewrite(tokens)
    body = markdown.renderer.render(tokens, markdown.options, {})
    html = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>README - local rendered review</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f8fa;color:#1f2328;font:16px/1.8 'Segoe UI','Microsoft YaHei',sans-serif}
main{max-width:1000px;background:white;margin:30px auto;padding:35px 45px;border:1px solid #d1d9e0;border-radius:6px}
h1,h2,h3{line-height:1.5}h1,h2{padding-bottom:9px;border-bottom:1px solid #d1d9e0}h2{margin-top:30px}
a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}img{max-width:100%;height:auto;display:block;margin:auto}
pre{padding:16px;background:#f6f8fa;overflow:auto;border-radius:5px;font-size:13px;line-height:1.6}
code{font-family:Consolas,monospace}table{border-collapse:collapse;max-width:100%;font-size:14px}
td,th{border:1px solid #d1d9e0;padding:6px 12px;text-align:left}tr:nth-child(even){background:#f6f8fa}
li{margin-bottom:8px}p{overflow-wrap:anywhere}.review-note{font-size:12px;color:#59636e;border-bottom:1px solid #d1d9e0;padding-bottom:14px}
@media(max-width:700px){main{margin:0;padding:18px;border:0}body{font-size:14px}td,th{padding:5px 7px}}
</style></head><body><main><p class="review-note">当前 README 源文件的本地渲染预览。GitHub 的实际排版可能略有差异。</p>'''
    destination = folder / 'readme-preview.html'
    destination.write_text(html + body + '</main></body></html>', encoding='utf-8')
    print(f'Rendered actual README: {destination}')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', default='release-dist/showcase-job')
    render(parser.parse_args().folder)
