"""中文页面规格协议示例；示例只展示结构，不是用户内容。"""
import json

_example = {
    "html_name": "index.html", "css_name": "site.css", "js_description": "",
    "description": "仅安排用户提供的个人介绍和已有内容。",
    "relationship": {"buttons": [], "links": [{"link_name":"首页", "jump_page":"index.html"}]},
    "practice_features": "语义导航与响应式阅读。",
    "additional_features": "",
    "page_style": "共享设计约定；本页按内容确定构图，不预设卡片或特效。",
    "is_main_page": True,
}
original_page_example = json.dumps(_example, ensure_ascii=False)
original_page_template = json.dumps([_example], ensure_ascii=False)
_local = dict(_example, relationship={**_example['relationship'], "imgs": []})
local_img_storage_page_example = json.dumps(_local, ensure_ascii=False)
local_img_storage_page_template = json.dumps([_local], ensure_ascii=False)

plan_output_format_prompt = """
保留示例中的键和值类型；可增加页面条目，不复制示例文案。links 使用 link_name/jump_page，buttons 使用 button_name/jump_page，禁止替换成 text/href。锚点使用已有文件名加 #id。所有页面互相可达，并能回到 index.html。jump_page 必须使用规划中的实际 html_name；没有提供外部链接时不添加。框架模式可以省略 css_name；原生 CSS 必须指定文件名。
Structure example: {page_template}
Return only valid JSON inside:
<designed_pages>
[{{page specification}}]
</designed_pages>
"""
plan_output_format_prompt_local_img = plan_output_format_prompt + """
Available local images: {local_img_storage}
仅按内容需要选用，src 保留原路径，不创造图片。
"""
refine_page_prompt = """
细化布局与内容组织，不能扩写履历事实。保持 html_name、css_name、relationship 和共享设计约定，不新增页面或链接。原始资料优先于页面描述；示例仅代表结构。
USER FACTS: {task_info}
Current specification: {page_info}
Structure example: {page_example}
DESIGN FEEDBACK: {feedback}
必须把合法 JSON 包在 <modified_page> 标签内，不得只输出裸对象或 Markdown：
<modified_page>
{{page specification}}
</modified_page>
"""
refine_page_local_img_prompt = refine_page_prompt + "\nAvailable local images (preserve paths): {local_img_storage}"
page_complete_prompt = """
根据已有页面补全当前页；保留共享风格、文件名、真实内容与跳转关系。不能虚构事实、联系方式或资源。
USER FACTS: {task_info}
Other pages: {other_pages_info}
Current page: {page_info}
DESIGN FEEDBACK: {feedback}
Return valid JSON in the existing tags:
<completed_page>
{{page specification}}
</completed_page>
<page_relationship>
[{{html_name and button_name for existing pages needing a link}}]
</page_relationship>
"""
page_complete_prompt_local_img = page_complete_prompt + "\nAvailable local images (preserve paths): {local_img_storage}"
