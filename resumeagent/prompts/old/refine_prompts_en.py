"""English visual refinement templates; historical exports are preserved."""
from .write_original_website_prompts_en import original_role, Tailwind_role, Boostrap_role, Materialize_role, Bulma_role

refine_text_task = """Compare the screenshot and code: correct fidelity, layout and readability first, then hierarchy and spacing. Change evidenced defects, preserve the shared brief, filenames and working features. Sparse content does not need filling.
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
