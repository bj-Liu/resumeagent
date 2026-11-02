"""中文生成模板；保持历史导出名称。"""
original_role = "Senior HTML/CSS frontend designer; embed necessary JavaScript in HTML."
Tailwind_role = "Senior Tailwind frontend designer."
Boostrap_role = "Senior Bootstrap frontend designer."
Materialize_role = "Senior Materialize frontend designer."
Bulma_role = "Senior Bulma frontend designer."

text_task = """按页面规格设计一个实际 HTML 页面，不构建后台或框架 SPA。依据内容决定布局与视觉重心，保留导航目标和本地图片路径。
Page specification: {page_info}
"""
text_img_task = """附图只用于学习构图、字级和空间关系；身份、事实与文案以 USER FACTS 为准。不要照搬参考网站的文字、品牌或图片。
Page specification: {page_info}
"""
img_task = text_img_task
original_output_format = "{feedback}\nOutput complete HTML and CSS in separate html/css fenced code blocks."
Tailwind_output_format = "{feedback}\nOutput complete Tailwind HTML in an html fenced code block."
Boostrap_output_format = "{feedback}\nOutput complete Bootstrap HTML in an html fenced code block."
Materialize_output_format = "{feedback}\nOutput complete Materialize HTML in an html fenced code block."
Bulma_output_format = "{feedback}\nOutput complete Bulma HTML in an html fenced code block."
write_original_prompt = "{role}\n{task}\n{output_format}"


