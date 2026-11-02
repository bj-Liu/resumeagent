"""English page specification examples; structural examples are not user facts."""
import json

_example = {
    "html_name": "index.html", "css_name": "site.css", "js_description": "",
    "description": "Organize only the supplied introduction and content.",
    "relationship": {"buttons": [], "links": [{"link_name":"Home", "jump_page":"index.html"}]},
    "practice_features": "Semantic navigation and responsive reading.",
    "additional_features": "",
    "page_style": "Shared site brief; content-specific composition, without preset cards or effects.",
    "is_main_page": True,
}
original_page_example = json.dumps(_example, ensure_ascii=False)
original_page_template = json.dumps([_example], ensure_ascii=False)
_local = dict(_example, relationship={**_example['relationship'], "imgs": []})
local_img_storage_page_example = json.dumps(_local, ensure_ascii=False)
local_img_storage_page_template = json.dumps([_local], ensure_ascii=False)

plan_output_format_prompt = """
Keep the example keys and value types; add page entries as needed, not example copy. Links use link_name/jump_page, buttons use button_name/jump_page; never substitute text/href. Anchors use an existing filename plus #id. All pages must be reachable and return to index.html. jump_page uses actual planned html_name values; no unsupplied external URLs. css_name is optional for framework mode and required for native CSS.
Structure example: {page_template}
Return only valid JSON inside:
<designed_pages>
[{{page specification}}]
</designed_pages>
"""
plan_output_format_prompt_local_img = plan_output_format_prompt + """
Available local images: {local_img_storage}
Use only when relevant; preserve src paths and never invent images.
"""
refine_page_prompt = """
Refine composition and organization, not resume facts. Preserve html_name, css_name, relationship and shared design brief; do not add pages or links. Source facts outrank page descriptions; the example is structure only.
USER FACTS: {task_info}
Current specification: {page_info}
Structure example: {page_example}
DESIGN FEEDBACK: {feedback}
Return only valid JSON inside the mandatory <modified_page> tags, not a naked object or Markdown:
<modified_page>
{{page specification}}
</modified_page>
"""
refine_page_local_img_prompt = refine_page_prompt + "\nAvailable local images (preserve paths): {local_img_storage}"
page_complete_prompt = """
Complete this page using existing pages; preserve shared style, filenames, supplied facts and navigation. Never invent biography, contact information or resources.
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
