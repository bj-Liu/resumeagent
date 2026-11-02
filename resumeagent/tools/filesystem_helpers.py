"""Low-level file/image I/O, separated to avoid agent import cycles."""
import os
import base64
import json
from pathlib import Path



def get_all_files_in_dir(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list


def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')


def get_openai_url(img_pth):
    img_pth = str(img_pth)
    if img_pth.startswith(('http://', 'https://', 'data:')):
        return img_pth
    end = img_pth.split(".")[-1].lower()
    if end == "jpg":
        end = "jpeg"
    base64_image = encode_image(img_pth)
    return f"data:image/{end};base64,{base64_image}"


def create_file(path):
    if not os.path.exists(path):
        directory = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, 'w') as f:
            f.write("{}")




def preview_metadata(root, files):
    """Return local file URIs and dimensions, never arbitrary file bodies or executable HTML."""
    from PIL import Image
    output = Path(root).resolve()
    artifacts = {}
    for kind in ('html','css','screenshot'):
        value = files.get(kind)
        if not value:
            continue
        path = Path(value).resolve()
        if not path.is_relative_to(output):
            raise PermissionError('Preview artifact escapes the run output directory')
        if not path.is_file():
            continue
        expected = {'html':'.html','css':'.css','screenshot':'.png'}[kind]
        if path.suffix.lower() != expected:
            raise PermissionError('Invalid preview artifact type')
        item = {'uri':path.as_uri(),'name':path.name,'bytes':path.stat().st_size,
                'mime_type':{'html':'text/html','css':'text/css','screenshot':'image/png'}[kind]}
        if kind == 'screenshot':
            with Image.open(path) as image:
                item.update(width=image.width,height=image.height)
        artifacts[kind] = item
    return {'available':'html' in artifacts and 'screenshot' in artifacts,
            'artifacts':artifacts,'preview_kind':'local_file_uris'}


def atomic_write(path, content):
    import tempfile
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.replace(destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return str(destination)



def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data, *, ensure_ascii=True):
    return atomic_write(path, json.dumps(data, ensure_ascii=ensure_ascii))
