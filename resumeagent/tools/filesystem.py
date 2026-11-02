"""Page persistence, local images, image-provider hooks, cleanup and rendering handoff."""
import logging
from pathlib import Path
import asyncio
import os
import json
import shutil
import re
from bs4 import BeautifulSoup
from PIL import Image
from resumeagent.tools.filesystem_helpers import atomic_write, create_file, get_all_files_in_dir
from resumeagent.utils import extract, format_profile, user_message
from resumeagent.prompts.process_img_prompts import get_process_img_prompt

logger = logging.getLogger(__name__)


class Filesystem:
    """Filesystem operations sharing the HomepageDesignAgent session state."""

    def get_img(self, description):
        """Keep the original image-provider hook without adding a new backend."""
        provider = getattr(self, 'image_client', None)
        if provider is None:
            import warnings
            warnings.warn('No image provider configured; keeping the original image reference.', RuntimeWarning)
            return None
        return provider.get_img(description)

    async def get_img_async(self, description):
        provider = getattr(self, 'image_client', None)
        if provider is not None and hasattr(provider, 'get_img_async'):
            return await provider.get_img_async(description)
        return await asyncio.to_thread(self.get_img, description)

    def save_img(self, img, img_content):
        name = os.path.basename(img_content['src'].split('?')[0]) or 'image.png'
        path = os.path.join(self.save_file, name)
        os.makedirs(self.save_file, exist_ok=True)
        img.save(path)
        img_content['src'] = name
        return img_content

    @staticmethod
    def validate_page_spec(page_info):
        from pathlib import PureWindowsPath
        if not isinstance(page_info, dict):
            raise ValueError('Page specification must be a dictionary')
        for key, extension in [('html_name', '.html'), ('css_name', '.css')]:
            value = page_info.get(key)
            if key == 'css_name' and not value:
                continue
            if not isinstance(value, str) or not value or Path(value).suffix.lower() != extension:
                raise ValueError('Invalid page filename')
            normalized = value.replace('\\','/')
            if Path(normalized).is_absolute() or PureWindowsPath(value).drive or '..' in normalized.split('/'):
                raise ValueError('Page path escapes the output directory')

    @classmethod
    def validate_plan(cls, pages):
        if not isinstance(pages, list) or not pages:
            raise ValueError('Website plan must contain pages')
        names = []
        for page in pages:
            cls.validate_page_spec(page)
            names.append(page['html_name'].replace('\\','/').casefold())
        if len(names) != len(set(names)):
            raise ValueError('Duplicate page filenames')

    def page_paths(self, page_info):
        self.validate_page_spec(page_info)
        root = Path(self.save_file).resolve()
        html = root / page_info['html_name']
        result = {'html':str(html), 'screenshot':str(html.with_suffix('.png'))}
        if not self.css_frame:
            if not page_info.get('css_name'):
                raise ValueError('css_name is required without a CSS framework')
            result['css'] = str(root / page_info['css_name'])
        for path in result.values():
            if not Path(path).resolve().is_relative_to(root):
                raise ValueError('Page path escapes the output directory')
        return result

    async def persist_html_css_async(self, page_info, html, css=None):
        paths = self.page_paths(page_info)
        if not html or (not self.css_frame and not css):
            raise ValueError('Missing generated HTML/CSS')
        if self.gen_img == 'Gen':
            html = await self.add_imgs_async(html)
        # Registry checks cancellation before this operation; check again after image work.
        from harness.context import CURRENT_EXECUTION
        scope = CURRENT_EXECUTION.get()
        if scope:
            scope.runtime.budget.check()
        atomic_write(paths['html'], html)
        if 'css' in paths:
            atomic_write(paths['css'], css)
        return {key:value for key,value in paths.items() if key != 'screenshot'}

    def read_page(self, page_info):
        paths = self.page_paths(page_info)
        return {'html':Path(paths['html']).read_text(encoding='utf-8'),
                'css':Path(paths['css']).read_text(encoding='utf-8') if 'css' in paths else None}

    def validate_page(self, page_info, require_screenshot=True):
        import hashlib
        paths = self.page_paths(page_info)
        code = self.read_page(page_info)
        soup = BeautifulSoup(code['html'], 'html.parser')
        if soup.find('html') is None or not code['html'].strip():
            raise ValueError('Invalid HTML document')
        if code['css'] is not None and not code['css'].strip():
            raise ValueError('Empty stylesheet')
        if require_screenshot:
            with Image.open(paths['screenshot']) as screenshot:
                screenshot.verify()
        files = {key:value for key,value in paths.items() if require_screenshot or key != 'screenshot'}
        fingerprints = {key:hashlib.sha256(Path(path).read_bytes()).hexdigest() for key,path in files.items()}
        return {'valid':True, 'files':files, 'fingerprints':fingerprints}

    @staticmethod
    def check_artifacts(files, fingerprints=None):
        import hashlib
        for key, path in files.items():
            file = Path(path)
            if not file.is_file():
                return False
            if fingerprints and key in fingerprints and hashlib.sha256(file.read_bytes()).hexdigest() != fingerprints[key]:
                return False
        return bool(files)

    def update_html_css(self, page_info, html, css):
        return asyncio.run(self.update_html_css_async(page_info, html, css))

    async def update_html_css_async(self, page_info, html, css):
        await self.tools.acall('filesystem.save_page', page_info=page_info, html=html, css=css)
        paths = self.page_paths(page_info)
        await self.tools.acall('browser.render', html_path=paths['html'], screenshot_path=paths['screenshot'])

    def delete_all_backups(self,directory):
        backup_folder = os.path.join(directory, "backup")
        try:
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)
                logger.info(f"已删除备用文件夹及其内容: {backup_folder}")
            else:
                logger.info(f"备用文件夹 {backup_folder} 不存在。")
        except Exception as e:
            logger.info(f"删除备用文件夹时出错: {e}")


    async def add_imgs_async(self,html_code):
        logger.info("begin add imgs")
        soup = BeautifulSoup(html_code, "html.parser")
        images = soup.find_all("img")
        scripts = soup.find_all("script")
        tasks = []

        tasks.append(self.add_imgs_to_background_async(html_code))
        for image in images:
            tasks.append(self.add_img_async(image))

        async def process_script(script):
            if script.string:
                script.string = await self.add_imgs_to_script_async(script.string)
        for script in scripts:
            tasks.append(process_script(script))
        await asyncio.gather(*tasks)
        return soup.prettify()


    async def add_imgs_to_background_async(self,html_code):

        pattern = r"url\(['\"]?(.*?)['\"]?\)"

        matchs = re.findall(pattern, html_code)

        for match in matchs:
            image_filename = match
            if "png" in image_filename or "jpg" in image_filename or "jpeg" in image_filename:
                img_name = os.path.basename(image_filename).split(".")[0]
                img_path = os.path.join(self.save_file,f"{img_name}.png")
                if os.path.exists(img_path):
                    continue
                text = format_profile(self.task)
                if text:
                    description = f"This is a image used in the background of the website. The website description is: {text}, The image name is {img_name}."
                else:
                    description = f"This is a image used in the background of the website. The image name is {img_name}."
                img = await self.get_img_async(description)
                if img:
                    create_file(img_path)
                    img.save(img_path)
                    logger.info(f"Image {img_path} has been added to the folder.")


    async def add_imgs_to_script_async(self,script):
        pattern = re.compile(r'{[^}]*\bimgsrc:\s*\'([^\']*)\'[^}]*\balt:\s*\'([^\']*)\'[^}]*}')
        for match in pattern.finditer(script):
            imgsrc = match.group(1)
            alt = match.group(2)
            img = await self.get_img_async(alt)
            if img:
                image = self.save_img(img,{"src":imgsrc,"alt":alt})
                new_imgsrc = image["src"]
                old_segment = match.group(0)
                new_segment = old_segment.replace(imgsrc,new_imgsrc)
                script = script.replace(old_segment,new_segment,1)
        return script


    async def add_img_async(self,img_content):
        try:
            src = img_content["src"]
            alt = img_content["alt"]
        except:
            return
        if os.path.exists(os.path.join(self.save_file,src)):
            return
        img = await self.get_img_async(alt)
        if img:
            self.save_img(img,img_content)


    def add_imgs(self,html_code):
        soup = BeautifulSoup(html_code, "html.parser")
        images = soup.find_all("img")
        scripts = soup.find_all("script")
        for image in images:
            try:
                src = image["src"]
                alt = image["alt"]
            except:
                continue
            if os.path.exists(os.path.join(self.save_file,src)):
                continue
            img = self.get_img(alt)
            if img:
                image = self.save_img(img,image)
        for script in scripts:
            if script.string:
                script.string = self.add_imgs_to_script(script.string)
        return soup.prettify()


    def add_imgs_to_script(self,script):
        pattern = re.compile(r'{[^}]*\bimgsrc:\s*\'([^\']*)\'[^}]*\balt:\s*\'([^\']*)\'[^}]*}')
        for match in pattern.finditer(script):
            imgsrc = match.group(1)
            alt = match.group(2)
            img = self.get_img(alt)
            if img:
                image = self.save_img(img,{"src":imgsrc,"alt":alt})
                new_imgsrc = image["src"]
                old_segment = match.group(0)
                new_segment = old_segment.replace(imgsrc,new_imgsrc)
                script = script.replace(old_segment,new_segment,1)
        return script


    def load_local_img_storage(self):
        local_img_storage_path = self.local_img_storage_path or self.save_file
        if os.path.exists(os.path.join(local_img_storage_path,f"local_img_storage_en.json")):
            with open(os.path.join(local_img_storage_path,f"local_img_storage_en.json"), "r",encoding="utf-8") as f:
                self.local_img_storage_en = json.load(f)
        if os.path.exists(os.path.join(local_img_storage_path,f"local_img_storage_zh.json")):
            with open(os.path.join(local_img_storage_path,f"local_img_storage_zh.json"), "r",encoding="utf-8") as f:
                self.local_img_storage_zh = json.load(f)
        if os.path.exists(os.path.join(local_img_storage_path,f"local_img_storage_zh.json")):
            if self.language == "en":
                self.local_img_storage = self.local_img_storage_en
            elif self.language == "zh":
                self.local_img_storage = self.local_img_storage_zh
        else:
            self.local_img_storage = []

        known_img_paths = [img["img_path"] for img in self.local_img_storage]
        all_files = get_all_files_in_dir(local_img_storage_path)
        img_files = []
        for file in all_files:
            if file.endswith(".png") or file.endswith(".jpg") or file.endswith(".jpeg"):
                img_name = os.path.basename(file)
                new_img_path = os.path.join(self.save_file,img_name)
                if os.path.abspath(file) != os.path.abspath(new_img_path):
                    shutil.copy(file,new_img_path)
                if img_name in known_img_paths:
                    continue
                img_files.append(new_img_path)
        asyncio.run(self.add_imgs_to_storage_async(img_files))
        with open(os.path.join(local_img_storage_path,"local_img_storage_en.json"), "w",encoding="utf-8") as f:
            json.dump(self.local_img_storage_en,f)
        with open(os.path.join(local_img_storage_path,"local_img_storage_zh.json"), "w",encoding="utf-8") as f:
            json.dump(self.local_img_storage_zh,f)

        if self.language == "en":
            self.local_img_storage = self.local_img_storage_en
        elif self.language == "zh":
            self.local_img_storage = self.local_img_storage_zh
        logger.info("Loaded local image entries: %s", len(self.local_img_storage))


    async def add_imgs_to_storage_async(self,img_files):
        tasks = []
        for img_path in img_files:
            tasks.append(self.add_img_to_storage_async(img_path))
        await asyncio.gather(*tasks)


    async def add_img_to_storage_async(self,img_path):
        with Image.open(img_path) as img:
            width,height = img.size
        img_name = os.path.basename(img_path)
        process_img_prompt = get_process_img_prompt(language=self.language)
        messages = user_message(process_img_prompt, [img_path])
        response = await self.get_answer_async(messages=messages)
        if not response:
            logger.warning("Failed to get the response.")
            return
        chinese_description = extract(response,"zh") or extract(response,"Chinese")
        english_description = extract(response,"en") or extract(response,"English")
        self.local_img_storage_en.append({"img_path":img_name,"description":english_description,"height":height,"width":width})
        self.local_img_storage_zh.append({"img_path":img_name,"description":chinese_description,"height":height,"width":width})
        logger.info(f"Image {img_name} has been added to the local image storage.")


    def clean(self):
        srcs = []
        for page in self.task_queue:
            html_name = page["html_name"]
            page_name = html_name.split(".")[0]
            page_img = os.path.join(self.save_file,f"{page_name}.png")
            srcs.append(page_img)
            html_path = os.path.join(self.save_file,html_name)
            if not os.path.exists(html_path):
                continue
            html_code = Path(html_path).read_text(encoding='utf-8')
            soup = BeautifulSoup(html_code, "html.parser")
            images = soup.find_all("img")
            for image in images:
                src = image["src"]
                srcs.append(src)
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    pattern = re.compile(r'{[^}]*\bimgsrc:\s*\'([^\']*)\'[^}]*\balt:\s*\'([^\']*)\'[^}]*}')
                    for match in pattern.finditer(script.string):
                        src = match.group(1)
                        srcs.append(src)
        all_files = get_all_files_in_dir(self.save_file)

        for file in all_files:
            if file.endswith(".png") or file.endswith(".jpg") or file.endswith(".jpeg"):
                img_name = os.path.basename(file)
                if img_name not in {os.path.basename(src) for src in srcs}:
                    os.remove(file)
                    logger.info(f"Image {img_name} has been removed.")

        self.delete_all_backups(self.save_file)
