"""English generation templates; historical exported names are preserved."""
original_role = "Senior HTML/CSS frontend designer; embed necessary JavaScript in HTML."
Tailwind_role = "Senior Tailwind frontend designer."
Boostrap_role = "Senior Bootstrap frontend designer."
Materialize_role = "Senior Materialize frontend designer."
Bulma_role = "Senior Bulma frontend designer."

text_task = """Build an actual HTML page, not a dashboard or framework SPA. Let content determine composition; preserve navigation targets and local image paths.
Page specification: {page_info}
"""
text_img_task = """Learn composition, type scale and spatial relationships from the attached reference; identity and copy come only from USER FACTS. Do not copy branded assets or reference biography.
Page specification: {page_info}
"""
img_task = text_img_task
original_output_format = "{feedback}\nOutput complete HTML and CSS in separate html/css fenced code blocks."
Tailwind_output_format = "{feedback}\nOutput complete Tailwind HTML in an html fenced code block."
Boostrap_output_format = "{feedback}\nOutput complete Bootstrap HTML in an html fenced code block."
Materialize_output_format = "{feedback}\nOutput complete Materialize HTML in an html fenced code block."
Bulma_output_format = "{feedback}\nOutput complete Bulma HTML in an html fenced code block."
write_original_prompt = "{role}\n{task}\n{output_format}"
