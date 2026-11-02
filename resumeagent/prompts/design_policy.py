"""Shared content-integrity and visual-design guidance for website generation.

Facts are strict; visual expression is intentionally flexible.
Public function signatures are kept compatible with the existing planner,
generator and refiner modules.
"""
import json


def facts_prompt(
    basic_information=None,
    academic_achievements=None,
    experience=None,
    professional_skills=None,
):
    """Serialize the user's supplied facts without silently dropping fields."""
    facts = {
        "basic_information": basic_information,
        "academic_achievements": academic_achievements,
        "experience": experience,
        "professional_skills": professional_skills,
    }
    return (
        "USER FACTS / 用户提供的原始资料（履历事实的唯一来源）:\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )


def assets_prompt(page_info=None, local_img_storage=None):
    """List real image assets; screenshots used as references are not assets."""
    relationship = (page_info or {}).get("relationship", {})
    images = relationship.get("imgs", []) if isinstance(relationship, dict) else []
    paths = []
    for item in list(images or []) + list(local_img_storage or []):
        path = (item.get("src") or item.get("img_path")) if isinstance(item, dict) else item
        if isinstance(path, str) and path.strip() and path not in paths:
            paths.append(path)

    if paths:
        return (
            "AVAILABLE IMAGE ASSETS / 可用图片资源:\n"
            + json.dumps(paths, ensure_ascii=False, indent=2)
            + "\nUse an image only when it genuinely supports this page. Preserve each selected "
              "path exactly; do not rename, rewrite, or fabricate paths. Choose sensible aspect "
              "ratios and object-fit behavior. A reference screenshot is visual guidance, not an "
              "asset that may be embedded."
        )

    return (
        "IMAGE ASSETS / 图片资源：当前页面没有提供可直接使用的图片文件。不要虚构头像、"
        "项目截图、学校或公司 Logo，也不要把参考截图当作网页图片嵌入。不要编造图片路径"
        "或随意引用图库图片来冒充用户作品。视觉丰富度可以通过排版、色块、CSS 几何图形、"
        "细线、纹理、渐变、留白和有意义的装饰实现；没有真实图片不等于页面必须单调。"
    )


def policy(language="en"):
    """Return the shared contract: factual accuracy is strict, design is not timid."""
    if language == "zh":
        return r"""【内容真实性：严格执行】
1. USER FACTS 是履历事实的唯一依据。设计参考、示例文案、参考截图中的人物信息、页面规划和设计反馈，都不能被当作用户的真实经历。
2. 可以对已有信息进行归纳、润色、拆分、重组和更清晰的表达；不能新增学校、学位、论文、奖项、公司、职位、项目成果、技术栈、性能数字、日期、联系方式、社交账号或外部链接。
3. 不要把“个人掌握某项技能”推断成“某个项目使用了该技术”；不要把研究兴趣写成已经实现的系统能力；不要把参与项目改写成独立主导，除非资料明确说明。
4. 用户只提供项目名称时，可以突出项目名称并为它设计有辨识度的版式，但不能自行补写项目目标、技术实现、职责、结果或部署情况。
5. 完整呈现与当前页面相关的已提供事实。不要为了追求简短而丢失重要经历、项目名称、奖项或技能；也不要把所有资料挤成一段。通过分组、标题、摘要、时间信息（仅限已提供）、列表和跨页面组织提高可读性。
6. 缺少某项信息时，省略对应字段或模块，不要出现“待补充”“暂无数据”等占位话术，也不要生成空的联系按钮或无效下载入口。

【视觉设计：鼓励原创，不要保守】
1. 事实必须真实，但布局、排版、色彩、空间关系、装饰语言和交互方案可以大胆原创。不要把“不能编造事实”误解为“不能创造视觉表达”。
2. 根据人物身份、内容类型、受众和用户反馈形成明确的艺术指导：确定视觉重心、版面网格、标题与正文的字级关系、色彩角色、留白节奏、分隔方式和重点内容的呈现方式。
3. 不要把每个模块都做成相同的圆角卡片。可以组合使用编辑式分栏、时间轴、编号内容行、项目案例带、图文错位、侧栏索引、全宽章节、细线分隔、局部色块、背景纹理和适量卡片。每种形式都要服务于内容。
4. 可以使用克制但有辨识度的渐变、CSS 几何装饰、柔和纹理、局部强调色和轻量微交互。避免无目的的蓝紫发光、过度玻璃拟态、随机 Emoji、装饰性按钮、无意义数字和为了炫技而加入的动画。
5. 页面不应默认采用 SaaS 后台、数据仪表盘或通用 AI Landing Page 的结构。不要每次都生成“顶部导航 + 居中大标题 + 三张功能卡 + 技能胶囊 + 渐变背景”的固定模板。
6. 首屏要有清晰的身份识别和内容重点，但不要为了制造视觉冲击而留下大块空白。姓名、身份、研究/职业方向、简介和关键入口应形成自然的层级，而不是机械地全部居中排列。
7. 不同页面保持一致的设计系统（色彩、字体、间距、导航和交互语言），但应根据内容采用不同构图；不要把同一布局复制到每一页。

【实现质量与体验】
1. 使用语义化 HTML、清晰的 class 命名和可维护 CSS。避免无必要的依赖；如果使用框架，遵循指定框架。
2. 桌面端要有明确的网格和合理的阅读宽度；移动端应重新组织布局，而不是简单缩小桌面页面。防止横向溢出、文字挤压和按钮过小。
3. 导航、锚点和按钮必须对应真实目标。只在确有价值时加入交互，例如页面导航、展开较长内容、复制真实联系方式或返回顶部。
4. 动效应轻量、可跳过；支持 prefers-reduced-motion。页面正文默认可见，不能依赖动画或 JavaScript 才能阅读。
5. 保证文字对比度、键盘焦点、图片替代文本和基本可访问性。不要用图标代替关键文字。
6. 输出完整、可运行的代码。保留规划中指定的文件名、页面关系、锚点和真实图片路径。"""

    return r"""CONTENT INTEGRITY — STRICT
1. USER FACTS are the only source of biographical evidence. Design references, examples, screenshot text, page plans and art direction are not facts about the user.
2. You may summarize, polish, reorganize and clarify supplied information. Never add schools, degrees, papers, awards, employers, roles, project outcomes, technology stacks, metrics, dates, contact details, social accounts or external links.
3. Do not infer that a project used a technology merely because the person lists that skill. Do not turn research interests into implemented capabilities. Do not claim ownership or leadership unless the supplied facts say so.
4. If only a project title is supplied, give the title a considered visual presentation; do not invent its goals, implementation, responsibilities, results or deployment status.
5. Preserve all supplied facts relevant to this page. Do not discard important experience, project titles, awards or skills merely to be concise, and do not cram everything into one paragraph. Use grouping, headings, summaries, dates only when supplied, lists and sensible distribution across pages.
6. If information is missing, omit the corresponding field or section. Do not add “coming soon”, fake data, empty contact buttons or nonfunctional download links.

VISUAL DESIGN — BE ORIGINAL, NOT TIMID
1. Facts must remain accurate; layout, typography, color, spatial composition, decorative language and interaction may be creative. “Do not invent facts” does not mean “do not create visual expression”.
2. Form a clear art direction from the person's identity, content, audience and explicit feedback. Make deliberate choices for visual focus, grid, type hierarchy, color roles, whitespace rhythm, separators and the presentation of important content.
3. Do not put every section in an identical rounded card. Mix editorial columns, timelines, numbered rows, project case-study bands, offset image/text compositions, side indexes, full-width sections, hairline rules, restrained color fields, subtle textures and selective cards when they serve the content.
4. Restrained gradients, CSS geometry, soft textures, accent colors and subtle micro-interactions are allowed when they contribute to the design. Avoid purposeless blue-purple glow, excessive glassmorphism, random emoji, decorative buttons, meaningless counters and animation added only to show off.
5. Do not default to a SaaS dashboard, analytics dashboard or generic AI landing page. Avoid repeating the formula “top navigation + centered oversized headline + three feature cards + skill pills + gradient background”.
6. Give the first screen a clear identity and focal point without leaving huge empty areas for drama. Name, role, research/professional focus, introduction and key actions should form a natural hierarchy rather than being mechanically centered.
7. Maintain one coherent design system across pages (colors, typography, spacing, navigation and interaction language), while varying composition to fit each page's content. Do not clone the same layout on every page.

IMPLEMENTATION AND EXPERIENCE
1. Use semantic HTML, clear class names and maintainable CSS. Avoid unnecessary dependencies and follow the selected framework when one is specified.
2. Use a deliberate desktop grid and readable line length. Recompose for mobile rather than merely shrinking the desktop layout. Prevent horizontal overflow, cramped text and undersized controls.
3. Navigation, anchors and buttons must lead to real destinations. Add interaction only when useful, such as navigation, expanding long content, copying a supplied contact detail or returning to the top.
4. Keep motion subtle and skippable; support prefers-reduced-motion. Main content must be visible without animation or JavaScript.
5. Maintain readable contrast, visible keyboard focus, image alt text and basic accessibility. Do not replace important text with icons.
6. Output complete, runnable code. Preserve planned filenames, page relationships, anchors and exact supplied image paths."""


def framework_instruction(css_frame, language="en", refining=False):
    """Describe the required implementation format without changing callers."""
    frame = "Bootstrap" if css_frame in ("Boostrap", "Bootstrap") else css_frame
    resources = {
        "Tailwind": '<script src="https://cdn.tailwindcss.com"></script>',
        "Bootstrap": '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">',
        "Materialize": '<link href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css" rel="stylesheet">',
        "Bulma": '<link href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css" rel="stylesheet">',
    }
    content_language = 'Chinese with lang="zh-CN"' if language == "zh" else 'English with lang="en"'
    if frame in resources:
        return (
            f"Framework: {frame}. Include this dependency: {resources[frame]} "
            "Use the framework for structure where helpful, not as a reason to make the page look like a dashboard. "
            f"Visible content language: {content_language}. "
            "Output one complete ```html code block. Embed necessary CSS and JavaScript in the HTML; "
            "do not output a separate JS file."
        )
    return (
        f"Use native HTML and CSS. Visible content language: {content_language}. "
        "Output a complete ```html code block and a complete ```css code block. "
        "The HTML must link the CSS file using the exact css_name specified in page_info. "
        "Embed necessary JavaScript in the HTML; do not output a separate JS file."
    )
