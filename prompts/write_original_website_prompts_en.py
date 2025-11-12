original_role = "You are an expert-level HTML developer, proficient in creating web pages using HTML, CSS, and JavaScript. (No need to output a separate JS file; embed JS directly in the HTML file.)"

Tailwind_role = "You are an expert-level Tailwind developer, proficient in creating web pages using the Tailwind CSS framework."

Boostrap_role = "You are an expert-level Bootstrap developer, proficient in creating web pages using the Bootstrap CSS framework."

Materialize_role = "You are an expert-level Materialize developer, proficient in creating web pages using the Materialize CSS framework."

Bulma_role = "You are an expert-level Bulma developer, proficient in creating web pages using the Bulma CSS framework."

img_task = """
The above image is a screenshot of the webpage we provide.
Page information is as follows: {page_info} (the filename of the button or link is its target page);
Your task is to build a single-page application based on the screenshot and page relationships.
- Ensure that the page you create matches the screenshot exactly.
- Pay attention to layout, image placement, image size, relevant text, buttons, links, etc., making them consistent with the screenshot.
- Match background color, text color, font size, font family, padding, margin, border, etc., exactly as in the screenshot.
- Use the exact text from the screenshot.
- Make sure that images do not cover text; text layers should always be on top.
- For images, try to use local images from the page information and do not change their file paths. 
- Avoid using images as background (e.g., background: url('https://placehold.co/1600x900')). You can use gradient colors or local images as background instead.
- Ensure that the generated page matches our provided page perfectly (layout, format, text, content)!
- Pay strict attention to image dimensions to ensure a visually appealing final rendering.
- You are encouraged to enhance interactivity and functionality using JavaScript (e.g., scrolling, clicking, hovering, color changes, click effects, page transitions, etc.) to make the page more practical and attractive to users.
"""

text_img_task = """
The above image is a screenshot of the reference webpage we provide.
Page information is as follows: {page_info} (the filename of the button or link is its target page);
Your task is to build a new webpage based on the structure and layout of the reference webpage and the provided page information.
- Modify based on the known information; avoid inventing content!
- Do not copy text from the reference webpage!
- The page does not need to be identical to the reference page; just learn from its strengths.
- Pay attention to background color, text color, font size, font family, padding, margin, border, etc.
- Ensure that images do not cover text; text layers should always be on top.
- For images, try to use local images from the page information and do not change their file paths. 
- Strictly pay attention to image dimensions to ensure a visually appealing final rendering.
- Make the page visually rich while maintaining coordination; for example, personal homepages should be simple, while technical sites should feel technical.
- Avoid using images as background (e.g., background: url('https://placehold.co/1600x900')). You can use gradient colors or local images as background instead.
- You are encouraged to use more colors, more buttons, more refined layout, and try effects like wave, gradient, scrolling, etc.
- Enhance interactivity and functionality using JavaScript (e.g., scrolling, clicking, hovering, color changes, click effects, page transitions, etc.) to make the page more practical and attractive to users.
"""

text_task = """
Page information is as follows: {page_info} (the filename of the button or link is its target page);
Your task is to build a single-page application based on the page information.
- Pay attention to background color, text color, font size, font family, padding, margin, border, etc.
- Ensure that images do not cover text; text layers should always be on top.
- For images, try to use local images from the page information and do not change their file paths. 
- Make the page visually rich while maintaining coordination; personal homepages should be simple.
- You are encouraged to use more colors, more buttons, more refined layout, and try effects like wave, gradient, scrolling, etc.
- Pay strict attention to image dimensions to ensure a visually appealing final rendering.
- Avoid using images as background (e.g., background: url('https://placehold.co/1600x900')). You can use gradient colors or local images as background instead.
- Enhance interactivity and functionality using JavaScript (e.g., scrolling, clicking, hovering, color changes, click effects, page transitions, etc.) to make the page more practical and attractive to users.
"""

original_output_format = """
{feedback}

Please output HTML (including JS code) and CSS code.
"""

Tailwind_output_format = """
{feedback}

Now output HTML code using the Tailwind CSS framework. (Be sure to include: <link href="https://cdn.jsdelivr.net/npm/tailwindcss@latest/dist/tailwind.min.css" rel="stylesheet"> in your HTML file. The website content should be in Chinese.)
"""

Boostrap_output_format = """
{feedback}

Now output HTML code using the Bootstrap CSS framework. (Be sure to include: <link href="https://cdn.jsdelivr.net/npm/bootstrap@latest/dist/css/bootstrap.min.css" rel="stylesheet"> in your HTML file. The website content should be in Chinese.)
"""

Materialize_output_format = """
{feedback}

Now output HTML code using the Materialize CSS framework. (Be sure to include: <link href="https://cdn.jsdelivr.net/npm/materialize-css@latest/dist/css/materialize.min.css" rel="stylesheet"> in your HTML file. The website content should be in Chinese.)
"""

Bulma_output_format = """
{feedback}

Now output HTML code using the Bulma CSS framework. (Be sure to include: <link href="https://cdn.jsdelivr.net/npm/bulma@latest/dist/css/bulma.min.css" rel="stylesheet"> in your HTML file. The website content should be in Chinese.)
"""

write_original_prompt = """
{role}
{task}
{output_format}
"""
