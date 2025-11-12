original_page_template = """
[
{
"html_name": {xxx.html},
"css_name": {css文件名},
"js_description": {为该页面设计的JavaScript功能},
"description": {页面描述},
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
"practice_features": {页面需要具备的实用功能},
"additional_features": {您想要添加到页面的其他功能},
"page_style": {page_style},
"is_main_page" : {true或false,如果页面是我们提供的图片请设置为true}
}
...
]
"""


original_page_example = """
{
    "html_name": "personal_homepage.html",
    "css_name": "personal_homepage.css",
    "js_description": "动态展示用户信息、项目、技能等，支持用户与不同内容模块的交互，包括个人信息的切换展示、项目详情展开、联系方式的点击复制等功能。",
    "description": "此页面展示用户的个人信息，包括头像、个人简介、项目经历、技能展示及联系方式。设计注重简洁现代，易于浏览和交互。",
    "relationship": {
        "buttons": [
            {"button_name": "查看项目", "action": "showProjects()"},
            {"button_name": "展开技能", "action": "expandSkills()"},
            {"button_name": "查看联系方式", "action": "showContactInfo()"},
            {"button_name": "返回顶部", "action": "scrollToTop()"},
            {"button_name": "切换暗色模式", "action": "toggleDarkMode()"},
            {"button_name": "返回", "jump_page": "previous_page.html"},
            {"button_name": "下一页", "jump_page": "next_page.html"}
        ],
        "links": [
            {"link_name": "GitHub", "jump_page": "https://github.com/username"},
            {"link_name": "LinkedIn", "jump_page": "https://linkedin.com/in/username"},
            {"link_name": "主页", "jump_page": "index.html"}
        ]
    },
    "practice_features": "个人信息展示，项目详情页，技能可视化展示，动态联系方式显示，暗色模式切换。",
    "additional_features": "支持点击复制功能用于联系方式，响应式布局适应不同设备尺寸，社交媒体图标与个人链接集成。",
    "page_style": "简洁现代的设计，使用渐变背景色和圆角元素，注重可读性和个性化元素。项目展示模块使用卡片式布局，支持动态展开和收起。",
    "is_main_page": true
}
    }
"""

local_img_storage_page_template = """
[
{
"html_name": {xxx.html},
"css_name": {css文件名},
"js_description": {为该页面设计的JavaScript功能},
"description": {页面描述},
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
    "src": {图片路径，必须是本地图片},
    "alt": {图片描述},
    "description": {图片在该页面中的作用}
        },
        ...
    ],
},
"practice_features": {页面需要具备的实用功能},
"additional_features": {您想要添加到页面的其他功能},
"page_style": {page_style},
"is_main_page" : {true或false,如果页面是我们提供的图片请设置为true}
}
...
]
"""

local_img_storage_page_example = """
{
    "html_name": "personal_homepage.html",
    "css_name": "personal_homepage.css",
    "js_description": "动态展示个人信息、项目、技能，并支持图片展示（如头像、项目图片）和用户交互功能。",
    "description": "此页面展示用户的个人信息，包括头像、项目展示、技能展示和联系方式。页面设计简洁现代，注重用户体验与视觉美观。",
    "relationship": {
        "buttons": [
            {"button_name": "查看项目", "action": "showProjects()"},
            {"button_name": "展开技能", "action": "expandSkills()"},
            {"button_name": "查看联系方式", "action": "showContactInfo()"},
            {"button_name": "切换暗色模式", "action": "toggleDarkMode()"},
            {"button_name": "返回顶部", "action": "scrollToTop()"},
            {"button_name": "返回", "jump_page": "previous_page.html"},
            {"button_name": "下一页", "jump_page": "next_page.html"}
        ],
        "links": [
            {"link_name": "GitHub", "jump_page": "https://github.com/username"},
            {"link_name": "LinkedIn", "jump_page": "https://linkedin.com/in/username"},
            {"link_name": "主页", "jump_page": "index.html"}
        ]
    },
    "imgs": [
        {
            "src": "profile_picture.png",
            "alt": "用户头像",
            "description": "显示用户的头像，用于个人主页的顶部个人信息部分。"
        },
        {
            "src": "project_1.png",
            "alt": "项目展示图1",
            "description": "展示项目1的图片，点击图片可查看项目详情。"
        },
        {
            "src": "project_2.png",
            "alt": "项目展示图2",
            "description": "展示项目2的图片，点击图片可查看项目详情。"
        },
        {
            "src": "background_image.jpg",
            "alt": "背景图片",
            "description": "个人主页的背景图片，提升页面的视觉美感。"
        }
    ],
    "practice_features": "个人信息展示，项目图片展示，动态技能展示，联系方式展示，支持图片点击查看详情。",
    "additional_features": "响应式设计，适应不同设备尺寸；暗色模式切换；社交媒体链接集成。",
    "page_style": "简洁现代的设计，使用渐变背景和图片元素，注重视觉效果和可读性。",
    "is_main_page": true
    }
"""


plan_output_format_prompt = """
请确保所有页面都可以通过按钮或链接访问，并且所有页面最终都可以跳转回主页(注意，你设计的html_name必须与其他page里的jump_page对应，不能出现无法跳转的情况)。
页面样例如下：
{page_template}

请严格按照以下格式输出(不允许额外信息):
<designed_pages>
{{设计的页面}}
</designed_pages>
"""

plan_output_format_prompt_local_img = """
以下是你可能要用到的本地图片信息（请注意，这些图片可能需要在你的设计中使用，且你需要尽量使用这些图片）：
{local_img_storage}

请确保所有页面都可以通过按钮或链接访问，并且所有页面最终都可以跳转回主页(注意，你设计的html_name必须与其他page里的jump_page对应，不能出现无法跳转的情况)。
页面样例如下：
{page_template}

请严格按照以下格式输出(不允许额外信息):
<designed_pages>
{{设计的页面}}
</designed_pages>
"""


refine_page_prompt = """
你是一个个人主页设计大师，你当前的任务是准确且基于事实地修改一个个人主页的细节。
{task_info}
以下页面是个人主页的页面之一。请完全根据提供的信息以及该页主题帮我丰富其细节，特别是展示个人成果、工作经历、项目经验。注意不要改变格式，不要凭空捏造！
修改后的页面应该是dict格式，不要有额外输出(不要添加新的链接到其他页面，同时不要修改任何html_name以免跳转失败)。
例如:
{page_example}
您可以通过丰富描述和其他方法(例如，添加布局描述，添加网页效果，添加实用功能，添加按钮等)来丰富页面细节，确保能够充分展示个人特色和优势。

页面是:
{page_info}(请注意button和link的跳转页面的文件名是它们的链接地址)

{feedback}

输出格式应该如下:
<modified_page>
{{你修改后的页面}}
</modified_page>
"""


refine_page_local_img_prompt = """
你是一个个人主页设计大师，你当前的任务是准确且基于事实地修改一个个人主页的细节。
{task_info}
以下页面是个人主页的页面之一。请完全根据我提供的信息帮我丰富其细节，要把我提供的信息准确完整的展示上去,特别是展示个人成果的方式、教育背景、工作经历、项目经验和专业技能,注意不要改变格式。
修改后的页面应该是dict格式，不要有额外输出(不要添加新的链接到其他页面，同时不要修改任何html_name以免跳转失败)。
例如:
{page_example}
您可以通过丰富描述和其他方法(例如，添加布局描述，添加网页效果，添加实用功能，添加按钮等)来丰富页面细节。

以下是你可能要用到的本地图片信息,如果你需要添加图片，请从以下图片中选择(请根据图片的内容，大小跟描述来选择图片，并决定图片的用途):
{local_img_storage}

页面是:
{page_info}(请注意button和link的跳转页面的文件名是它们的链接地址,同时不要修改页面的html_name)

{feedback}

输出格式应该如下:
<modified_page>
{{你修改后的页面}}
</modified_page>
"""

page_complete_prompt = """
你是一个个人主页设计大师，你的任务是准确且基于事实地完成和完善一个未完成的个人主页。

其他页面信息如下:
{other_pages_info}

当前页面信息如下:
{page_info}(请注意button和link的跳转页面的文件名是它们的链接地址,同时不要修改页面的html_name)

{feedback}(请特别关注feedback，并满足用户的需求)

请根据其他页面的信息和当前页面的已知信息(注意页面之间的跳转关系)，完成和完善此页面的信息，请特别注重展示个人信息、成果、教育背景、工作经历、项目经验和专业技能的方式，确保能够突出个人形象,并考虑哪些页面需要设计按钮以跳转到当前页面。

你的输出应该是以下格式:
思考步骤:
{{你的思考步骤}}

<completed_page>
{{你完成和完善的页面，不要改变或添加或删除页面的原始键，你可以修改键的值，页面应该是dict格式}}
</completed_page>

<page_relationship>
{{需要设计按钮以跳转到当前页面的页面名称，输出格式应该是一个列表。例如:[{{"html_name":"index.html","button_name":"jump"}},{{"html_name":"home.html","button_name":"jump"}}]}}
</page_relationship>

"""

page_complete_prompt_local_img = """
你是一个个人主页设计大师，你的任务是根据已知信息准确且基于事实地完成和完善一个未完成的个人主页。

其他页面信息如下:
{other_pages_info}

当前页面信息如下:
{page_info}(请注意button和link的跳转页面的文件名是它们的链接地址,同时不要修改页面的html_name)

{feedback}

以下是你可能要用到的本地图片信息（请注意，这些图片可能需要在你的设计中使用，且你需要尽量使用这些图片）：
{local_img_storage}

请根据其他页面的信息和当前页面的已知信息(注意页面之间的跳转关系)，完成和完善此页面的信息，并考虑哪些页面需要设计按钮以跳转到当前页面，删除无用的按钮
请特别注重展示个人成果、教育背景、工作经历、项目经验和专业技能的方式，确保能够突出个人形象。

你的输出应该是以下格式:
思考步骤:
{{你的思考步骤}}

<completed_page>
{{你完成和完善的页面，不要改变或添加或删除页面的原始键，你可以修改键的值，页面应该是dict格式}}
</completed_page>

<page_relationship>
{{需要设计按钮以跳转到当前页面的页面名称，输出格式应该是一个列表。例如:[{{"html_name":"index.html","button_name":"jump"}},{{"html_name":"home.html","button_name":"jump"}}]}}
</page_relationship>
"""

if __name__ == "__main__":
    import json
    print(json.loads(local_img_storage_page_example))