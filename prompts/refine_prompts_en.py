original_role  = "You are an expert HTML developer, skilled in creating webpages using HTML, CSS, and JavaScript. (No need to output separate JS files; embed all JS code directly in the HTML.)"

Tailwind_role  = "You are an expert Tailwind developer, proficient in building webpages using the Tailwind CSS framework."

Boostrap_role  = "You are an expert Bootstrap developer, proficient in building webpages using the Bootstrap CSS framework."

Materialize_role = "You are an expert Materialize developer, proficient in building webpages using the Materialize CSS framework."

Bulma_role = "You are an expert Bulma developer, proficient in building webpages using the Bulma CSS framework."


refine_img_task = """
The first image is a screenshot of the target webpage, and the second image is a screenshot of the webpage you have already built.
{local_img_storage}
Page information:
{page_info} (button and link targets correspond to their respective file names)

Your goal is to modify the code of the second webpage to make it more closely match the first image.

- Ensure the page layout matches the screenshot exactly.
- Pay attention to layout, text, buttons, and links.
- Match background colors, text colors, font sizes, font families, padding, margins, and borders exactly.
- Use the exact text from the screenshot; do not modify it.
- Avoid placeholder backgrounds (e.g., background: url('https://placehold.co/1600x900')); you may use gradients or local images instead.
- For images, use the local images specified in the page information and do not change file paths.
- Strictly ensure image dimensions are correct for a visually pleasing final page.
- You may enhance interactivity with JavaScript features (scrolling, click events, hover effects, color changes, transitions, page switching, etc.) to make the page both functional and visually appealing.
"""


refine_img_text_task = """
The first image is a reference webpage screenshot, and the second image is a screenshot of the webpage you have already built.
{local_img_storage}
Page information:
{page_info} (button and link targets correspond to their respective file names)

Your goal is to modify the second webpage's code to follow the layout and structure of the first image while meeting the page information requirements.
- Make modifications based on known information only; do not fabricate content.
- Do not copy the text from the reference page; add text as needed according to user requirements.
- You may add or modify JavaScript, CSS layout, or HTML elements to improve the page.
- Pay attention to background colors, text colors, font sizes, font families, padding, margins, and borders.
- Aim for a rich but visually balanced design; keep personal homepage layouts clean.
- Strictly ensure image dimensions are correct for a visually pleasing result.
- Use local images as specified in the page information and do not modify file paths.
- Ensure images do not cover text; text layers should always be on top.
- Encourage the use of colors, buttons, and effects (waves, gradients, scrolling) to enhance aesthetics.
- Avoid placeholder backgrounds; use gradients or local images instead.
- Consider functionality and usability when modifying the code.
- Analyze headers, navigation, content arrangement, sidebars, footers, visuals, layout, calls to action, responsiveness, and other features to optimize the page.
- Think about how code changes can make the page meet requirements (e.g., adding buttons or text content).
- You may enhance interactivity using JavaScript features (scroll, click, hover, color changes, transitions, page switching, etc.) to ensure usability and visual appeal.
"""


refine_text_task = """
{local_img_storage}
Page information:
{page_info} (button and link targets correspond to their respective file names)

Your task is to modify the code according to user feedback to meet their requirements.
- You may add or modify JavaScript, CSS layout, or HTML elements based on feedback.
- Pay attention to background colors, text colors, font sizes, font families, padding, margins, and borders.
- Aim for a visually rich and coordinated layout; personal homepages should remain clean.
- Ensure images follow the page information and maintain correct file paths.
- Ensure images do not cover text; text layers should always be on top.
- Encourage the use of colors, buttons, effects (waves, gradients, scrolling) to enhance the page.
- Avoid placeholder backgrounds; use gradients or local images instead.
- Consider functionality and usability when modifying the code.
- Analyze headers, navigation, content arrangement, sidebars, footers, visuals, layout, calls to action, responsiveness, and other features to optimize the page.
- Think about how code changes can make the page meet requirements (e.g., adding buttons or text content).
- You may enhance interactivity using JavaScript features (scroll, click, hover, color changes, transitions, page switching, etc.) to ensure usability and visual appeal.
"""


refine_feedback_task = """
{local_img_storage}
Page information:
{page_info} (button and link targets correspond to their respective file names)

Your task is to modify the code according to user feedback to meet their requirements.
- Make changes strictly according to known information; do not fabricate content.
- Pay close attention to user feedback and adjust the code accordingly to meet user needs.
- You may add or modify JavaScript, CSS layout, or HTML elements based on feedback.
- Pay attention to background colors, text colors, font sizes, font families, padding, margins, and borders.
- Aim for a visually rich and coordinated layout; personal homepages should remain clean.
- Ensure images follow the page information and maintain correct file paths.
- Ensure images do not cover text; text layers should always be on top.
- Encourage the use of colors, buttons, effects (waves, gradients, scrolling) to enhance the page.
- Avoid placeholder backgrounds; use gradients or local images instead.
- Consider functionality and usability when modifying the code.
- Analyze headers, navigation, content arrangement, sidebars, footers, visuals, layout, calls to action, responsiveness, and other features to optimize the page.
- Think about how code changes can make the page meet requirements (e.g., adding buttons or text content).
- You may enhance interactivity using JavaScript features (scroll, click, hover, color changes, transitions, page switching, etc.) to ensure usability and visual appeal.
"""


refine_original_output_format = """
The current page code is as follows:
HTML code:
{html_code}
CSS code:
{css_code}

{feedback}

Please provide a modification plan, then output the updated HTML (including embedded JS) and CSS code.

Output format:
Modification plan:
1.
2.
...

Updated HTML:

Updated CSS:
"""


refine_Tailwind_output_format = """
The current page code is as follows:
HTML code using Tailwind CSS:
{html_code}

{feedback}

Please provide a modification plan, then output the updated HTML code.

Output format:
Modification plan:
1.
2.
...

Updated HTML:
"""


refine_Boostrap_output_format = """
The current page code is as follows:
HTML code using Bootstrap CSS:
{html_code}

{feedback}

Please provide a modification plan, then output the updated HTML code.

Output format:
Modification plan:
1.
2.
...

Updated HTML:
"""


refine_Materialize_output_format = """
The current page code is as follows:
HTML code using Materialize CSS:
{html_code}

{feedback}

Please provide a modification plan, then output the updated HTML code.

Output format:
Modification plan:
1.
2.
...

Updated HTML:
"""


refine_Bulma_output_format = """
The current page code is as follows:
HTML code using Bulma CSS:
{html_code}

{feedback}

Please provide a modification plan, then output the updated HTML code.

Output format:
Modification plan:
1.
2.
...

Updated HTML:
"""


refine_prompt = """
{role}
{task}
{output_format}
"""
