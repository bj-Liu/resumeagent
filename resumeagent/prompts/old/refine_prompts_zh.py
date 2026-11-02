"""中文视觉修改模板；保留历史模板导出。"""
from .write_original_website_prompts_zh import original_role, Tailwind_role, Boostrap_role, Materialize_role, Bulma_role

refine_text_task = """对照截图与当前代码，优先修正事实、布局和可读性问题，再改进字级与留白。只改有依据的问题，保留共享设计约定、页面路径和有效功能。不要求把内容稀少的页面填满。
Page specification: {page_info}
Available local images (preserve paths): {local_img_storage}
"""
refine_feedback_task = refine_text_task
refine_img_task = refine_text_task
refine_img_text_task = refine_text_task
refine_original_output_format = "Current HTML: {html_code}\nCurrent CSS: {css_code}\n{feedback}\nReturn complete html and css fenced code blocks."
refine_Tailwind_output_format = "Current Tailwind HTML: {html_code}\n{feedback}\nReturn a complete html fenced code block."
refine_Boostrap_output_format = "Current Bootstrap HTML: {html_code}\n{feedback}\nReturn a complete html fenced code block."
refine_Materialize_output_format = "Current Materialize HTML: {html_code}\n{feedback}\nReturn a complete html fenced code block."
refine_Bulma_output_format = "Current Bulma HTML: {html_code}\n{feedback}\nReturn a complete html fenced code block."
refine_prompt = "{role}\n{task}\n{output_format}"

