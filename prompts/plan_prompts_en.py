original_page_template = """
[
{
"html_name": {xxx.html},
"css_name": {css_filename},
"js_description": {JavaScript functionality designed for this page},
"description": {page description},
"relationship": {
"buttons":[
        {
        "button_name" : {button_name},
        "jump_page" : {target_page}
        },
        ...
    ],
"links":[
        {
        "link_name" : {link_name},
        "jump_page" : {target_page}
        },
        ...
    ]
},
"practice_features": {practical features required for this page},
"additional_features": {additional features you want to add to this page},
"page_style": {page_style},
"is_main_page" : {true or false, set to true if the page is provided by us as the main page}
}
...
]
"""


original_page_example = """
{
    "html_name": "personal_homepage.html",
    "css_name": "personal_homepage.css",
    "js_description": "Dynamically displays user information, projects, skills, and more. Supports interactive switching of personal info, expanding project details, and copying contact info with one click.",
    "description": "This page presents the user's personal information, including avatar, bio, project experience, skill showcase, and contact info. The design focuses on modern simplicity and good readability.",
    "relationship": {
        "buttons": [
            {"button_name": "View Projects", "action": "showProjects()"},
            {"button_name": "Expand Skills", "action": "expandSkills()"},
            {"button_name": "View Contacts", "action": "showContactInfo()"},
            {"button_name": "Back to Top", "action": "scrollToTop()"},
            {"button_name": "Toggle Dark Mode", "action": "toggleDarkMode()"},
            {"button_name": "Back", "jump_page": "previous_page.html"},
            {"button_name": "Next", "jump_page": "next_page.html"}
        ],
        "links": [
            {"link_name": "GitHub", "jump_page": "https://github.com/username"},
            {"link_name": "LinkedIn", "jump_page": "https://linkedin.com/in/username"},
            {"link_name": "Home", "jump_page": "index.html"}
        ]
    },
    "practice_features": "Displays personal info, project details, skill visualization, dynamic contact info display, dark mode.",
    "additional_features": "Click-to-copy feature for contact info, responsive layout for multiple devices, integrated social icons and links.",
    "page_style": "Modern minimalist with gradient backgrounds and rounded components. Card-style layout for project display with expandable sections.",
    "is_main_page": true
}
"""


local_img_storage_page_template = """
[
{
"html_name": {xxx.html},
"css_name": {css_filename},
"js_description": {JavaScript functionality designed for this page},
"description": {page description},
"relationship": {
"buttons":[
        {
        "button_name" : {button_name},
        "jump_page" : {target_page}
        },
        ...
    ],
"links":[
        {
        "link_name" : {link_name},
        "jump_page" : {target_page}
        },
        ...
    ],
"imgs": [
    {
    "src": {image path, must be local},
    "alt": {image description},
    "description": {image usage within the page}
        },
        ...
    ],
},
"practice_features": {practical features required for this page},
"additional_features": {additional features you want to add},
"page_style": {page_style},
"is_main_page" : {true or false, set to true if this page uses our provided main image}
}
...
]
"""


local_img_storage_page_example = """
{
    "html_name": "personal_homepage.html",
    "css_name": "personal_homepage.css",
    "js_description": "Dynamically displays info, projects, skills, and supports image display (avatar, project images) plus interactivity.",
    "description": "This page shows personal info, including avatar, project showcases, skills, and contact details. Clean modern design focusing on visual experience.",
    "relationship": {
        "buttons": [
            {"button_name": "View Projects", "action": "showProjects()"},
            {"button_name": "Expand Skills", "action": "expandSkills()"},
            {"button_name": "View Contacts", "action": "showContactInfo()"},
            {"button_name": "Toggle Dark Mode", "action": "toggleDarkMode()"},
            {"button_name": "Back to Top", "action": "scrollToTop()"},
            {"button_name": "Back", "jump_page": "previous_page.html"},
            {"button_name": "Next", "jump_page": "next_page.html"}
        ],
        "links": [
            {"link_name": "GitHub", "jump_page": "https://github.com/username"},
            {"link_name": "LinkedIn", "jump_page": "https://linkedin.com/in/username"},
            {"link_name": "Home", "jump_page": "index.html"}
        ]
    },
    "imgs": [
        {
            "src": "profile_picture.png",
            "alt": "User avatar",
            "description": "Displayed at the top personal info section."
        },
        {
            "src": "project_1.png",
            "alt": "Project image 1",
            "description": "Shows project 1 with clickable detail view."
        },
        {
            "src": "project_2.png",
            "alt": "Project image 2",
            "description": "Shows project 2 with interactive details."
        },
        {
            "src": "background_image.jpg",
            "alt": "Background image",
            "description": "Used as background to improve visual aesthetics."
        }
    ],
    "practice_features": "Displays personal info, project images, dynamic skill display, contact info, image click-to-view.",
    "additional_features": "Responsive design, dark mode, social media integration.",
    "page_style": "Modern gradient background, visually polished layout.",
    "is_main_page": true
}
"""


plan_output_format_prompt = """
Ensure all pages can be accessed via buttons or links, and all pages can navigate back to the homepage (Note: html_name must match the jump_page in other pages. No dead links allowed).
Page example:
{page_template}

Strict output format:
<designed_pages>
{{designed pages}}
</designed_pages>
"""


plan_output_format_prompt_local_img = """
Below are the local images you may need (please try to use them when appropriate):
{local_img_storage}

Ensure all pages are connected via buttons/links and can return to home. The html_name must match jump_page references.

Page example:
{page_template}

Strict output format:
<designed_pages>
{{designed pages}}
</designed_pages>
"""


refine_page_prompt = """
You are a master of personal homepage design. Your task is to accurately and factually refine page details.
{task_info}
Below is one page of the homepage. Enrich the details based on the given info and page theme—especially personal achievements, work experience, and project experience. Do not change the format or invent facts!
Output must be a dict. No extra output. Do not add new links/pages. Do not modify html_name.
Example:
{page_example}

You may enrich layout, visual effects, functional elements, etc., to highlight personal strengths.

Page:
{page_info} (Note: button/link jump_page must match actual filenames)

{feedback}

Output format:
<modified_page>
{{your modified page}}
</modified_page>
"""


refine_page_local_img_prompt = """
You are a personal homepage design master. Your task is to refine the page based on accurate info.
{task_info}
Below is one page of the homepage. Enrich the details while accurately including user-provided info—achievements, education, work experience, project experience, technical skills. Do not change format or invent content.
Output must be a dict. No extra output. Do not modify html_name.

Example:
{page_example}

You may enrich layout, effects, functional components.

Below are the local images you may use (choose only appropriate ones):
{local_img_storage}

Page:
{page_info}

{feedback}

Output format:
<modified_page>
{{your modified page}}
</modified_page>
"""


page_complete_prompt = """
You are a personal homepage design master. Your task is to accurately complete and refine an unfinished page.

Other pages:
{other_pages_info}

Current page:
{page_info}

{feedback} (pay special attention)

Complete the page based on existing pages and maintain page relationships. Highlight personal info, achievements, education, work history, projects, and skills.

Output format:
Thought process:
{{your reasoning}}

<completed_page>
{{completed page in dict format}}
</completed_page>

<page_relationship>
{{list of pages that need buttons linking to this page}}
</page_relationship>
"""


page_complete_prompt_local_img = """
You are a personal homepage design master. Your task is to accurately complete and refine a homepage page.

Other pages:
{other_pages_info}

Current page:
{page_info}

{feedback}

Below are the local images you may use:
{local_img_storage}

Ensure consistency with other pages and maintain jump relationships. Remove useless buttons.

Highlight achievements, education, work experience, project experience, skills.

Output format:
Thought process:
{{your reasoning}}

<completed_page>
{{completed page in dict format}}
</completed_page>

<page_relationship>
{{list of pages that need buttons linking to this page}}
</page_relationship>
"""

if __name__ == "__main__":
    import json
    print(json.loads(local_img_storage_page_example))
