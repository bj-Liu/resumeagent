"""Design-aware HTML generation with the established public API and output protocol."""
import json

from .design_policy import facts_prompt, assets_prompt, policy, framework_instruction
from .design_references import (
    PROMPT_VERSION,
    REFERENCES,
    select_references,
    reference_prompt,
)


def page_references(profile, feedback, page_info):
    """Reuse the references selected by Planner; otherwise select relevant inspiration."""
    style = (page_info or {}).get("page_style", "")
    prefix = f"[Design brief {PROMPT_VERSION}: "
    if isinstance(style, str) and style.startswith(prefix):
        names = style.split("]", 1)[0][len(prefix):].split(", ")
        valid = tuple(name for name in names if name in REFERENCES)
        if valid:
            return valid[:2]
    return select_references(profile, feedback, page_info)


def _page_info_text(page_info):
    if isinstance(page_info, (dict, list)):
        return json.dumps(page_info, ensure_ascii=False, indent=2)
    return str(page_info or "")


def _generation_guidance(language="en"):
    """Detailed execution guidance: rich visual output without fabricated facts."""
    if language == "zh":
        return r"""【网页设计与实现任务】
你不是在填写一个固定网页模板，而是在为这个具体的人设计一张有辨识度、内容完整、可实际使用的个人主页页面。请把页面规格当作本页的内容与功能约定，并把 USER FACTS 当作事实依据。

一、先理解页面，再决定构图
- 判断本页的目标、主要读者和最重要的信息。首页、教育经历、研究成果、项目案例、技能索引不应使用完全相同的版式。
- 根据内容决定视觉重心和信息顺序。可以使用非对称双栏、编辑式网格、时间轴、编号列表、项目案例带、侧栏索引、全宽章节、图文错位或少量卡片；选择最适合当前内容的组合。
- 首屏要让人快速理解“这是谁、主要做什么、有什么值得继续看”，但不要机械地使用居中大标题和空洞留白。姓名、身份、简介、方向和关键入口应形成明确层次。
- 页面内容应有足够细节。把用户提供的经历、项目、奖项、技能和研究方向组织成可阅读的内容区块，不要把丰富资料压缩成几句泛泛的介绍，也不要为了填充而编造内容。

二、建立明确的视觉语言
- 结合用户反馈与参考图，确定背景、正文、强调色和辅助色；明确字体层级、行高、容器宽度、网格、边距和章节间距。
- 让标题、正文、日期、分类标签、注释和链接有清晰的视觉层次。重要内容应通过字号、位置、对齐、留白或局部色彩突出，而不是所有东西都加粗或装进卡片。
- 允许有设计感的细线、局部色块、柔和渐变、CSS 几何装饰、轻纹理、图标和微交互，但每一种视觉元素都要服务于内容或阅读体验。
- 避免套用常见 AI 模板：整页蓝紫渐变、所有区块同款圆角卡片、技能百分比条、无意义统计数字、随机 Emoji、重复胶囊标签和装饰性按钮。
- 参考网站只借鉴构图、排版节奏和视觉处理方式，不复制它的品牌、文案或人物信息。用户明确指定的风格和颜色优先于自动参考。

三、内容呈现与事实边界
- 认真读取全部 USER FACTS 和本页 page_info。保留本页相关的真实信息、项目名称、时间、职责、成果和技能，不要无故删减。
- 可以把已有文字改写得更清楚、更适合网页阅读，但不能新增没有依据的事实。项目名称不能自动扩写成项目介绍；技能列表不能自动变成某个项目的技术栈。
- 如果内容较多，通过分组、摘要、展开区域、编号条目或合适的页面分配来组织；不要把所有内容塞在首屏，也不要为了简洁把关键细节删掉。
- 不要生成虚构头像、论文封面、学校 Logo、公司 Logo、项目截图、客户评价、下载文件或社交链接。图片只能使用可用资源清单中的真实路径。

四、交互、响应式与可访问性
- 导航和页面关系必须使用 page_info 中的真实文件名与链接目标。按钮必须有真实作用；没有实际功能时不要添加按钮。
- 交互可以包括导航高亮、锚点滚动、真实联系方式复制、内容展开、图片查看等，但只实现当前资料和页面真正支持的功能。
- 桌面端布局应有明确网格与舒适阅读宽度；移动端重新排列区块、导航和文字，不允许简单缩小桌面布局。
- 使用语义化 HTML、清晰 CSS、可见键盘焦点、足够对比度和 prefers-reduced-motion。正文默认可见，不依赖动画或 JavaScript 才显示。

五、交付要求
- 生成完整、可运行的页面代码，不要只给设计建议或伪代码。
- 严格遵守下方指定的 HTML/CSS 输出格式、文件名、页面关系和框架要求。
- 不要在代码块之外输出解释。"""
    return r"""WEBSITE DESIGN AND IMPLEMENTATION TASK
You are not filling a generic template. You are designing a distinctive, content-rich, usable page for this specific person. Treat page_info as the page's content/function contract and USER FACTS as the only biographical evidence.

1. Understand the page before choosing its composition
- Identify this page's purpose, audience and most important information. Home, education, research, project case studies and skills should not all use the same layout.
- Let the content determine visual focus and reading order. Consider asymmetric columns, editorial grids, timelines, numbered rows, project case-study bands, side indexes, full-width sections, offset image/text compositions or selective cards. Choose a composition that suits this page.
- The first screen should quickly communicate who the person is, what they focus on and why a visitor should continue. Avoid a mechanically centered oversized headline or empty hero. Establish a clear hierarchy among name, role, introduction, focus and useful actions.
- Keep the page content substantial enough to represent the supplied material. Organize real experience, projects, awards, skills and research interests into readable sections. Do not compress a rich profile into a few generic sentences, and do not fabricate content to make it look full.

2. Establish a deliberate visual language
- Use the user's feedback and visual references to define background, text, accent and supporting colors; make deliberate choices for typography, line-height, container width, grid, margins and section rhythm.
- Give headings, body text, dates, category labels, captions and links distinct visual roles. Emphasize important information through scale, placement, alignment, whitespace or selective color—not by bolding everything or putting everything in cards.
- Purposeful hairlines, color fields, soft gradients, CSS geometry, subtle texture, icons and micro-interactions are welcome when they support content or usability.
- Avoid generic AI patterns: full-page blue-purple gradients, identical rounded cards for every section, skill percentage meters, meaningless statistics, random emoji, repetitive pill tags and decorative buttons.
- Learn composition, typographic rhythm and visual treatment from reference websites; do not copy their branding, text or personal information. Explicit user preferences and colors outrank automatic references.

3. Content and factual boundaries
- Read all USER FACTS and the current page_info carefully. Preserve the real information relevant to this page, including supplied project names, dates, responsibilities, outcomes and skills. Do not omit details without a reason.
- You may clarify and rewrite supplied text for the web, but never add unsupported facts. Do not turn a project title into an invented project description or turn a general skill list into a project's technology stack.
- When information is extensive, organize it with groups, summaries, expandable details, numbered entries or sensible page distribution. Do not cram everything into the hero, and do not remove important details merely to make the page shorter.
- Do not fabricate portraits, paper covers, university/company logos, project screenshots, testimonials, downloadable files or social links. Images may only use exact paths in the available asset list.

4. Interaction, responsive behavior and accessibility
- Navigation and page relationships must use the exact filenames and destinations in page_info. Every button must do something real; do not add controls with no actual function.
- Useful interactions may include active navigation, anchor navigation, copying a supplied contact detail, expanding long content or viewing an available image. Implement only what the supplied information and page support.
- Use a deliberate desktop grid and comfortable reading width. Recompose navigation, sections and text for mobile; do not merely shrink the desktop layout.
- Use semantic HTML, maintainable CSS, visible keyboard focus, readable contrast and prefers-reduced-motion. Main content must remain visible without animation or JavaScript.

5. Deliverable
- Produce complete, runnable page code, not just design advice or pseudocode.
- Follow the exact HTML/CSS output format, filenames, page relationships and framework requirements below.
- Do not add explanations outside the code blocks."""


def get_write_original_website_prompt(
    basic_information=None,
    academic_achievements=None,
    experience=None,
    professional_skills=None,
    img=None,
    page_info=None,
    css_frame=None,
    feedback="",
    language="en",
):
    """Build a complete generation prompt while preserving the historical API."""
    profile = dict(
        basic_information=basic_information,
        academic_achievements=academic_achievements,
        experience=experience,
        professional_skills=professional_skills,
    )

    if language == "zh":
        from .write_original_website_prompts_zh import text_task, text_img_task, img_task
        role = (
            "你是一位资深个人品牌与作品集设计师，同时是精通 HTML、CSS 和 JavaScript 的前端工程师。"
            "你需要把真实资料转化为有个性、有层次、可访问的网页，而不是套用通用模板。"
        )
    else:
        from .write_original_website_prompts_en import text_task, text_img_task, img_task
        role = (
            "You are a senior personal-brand and portfolio designer as well as an expert "
            "HTML/CSS/JavaScript frontend engineer. Turn supplied facts into a distinctive, "
            "well-structured, usable website rather than applying a generic template."
        )

    if img:
        task_template = text_img_task if any(profile.values()) else img_task
    else:
        task_template = text_task

    return "\n\n".join(
        part for part in (
            role,
            facts_prompt(**profile),
            (
                "DESIGN REQUEST / 设计要求（只定义视觉与体验，不是履历事实）:\n"
                + (feedback or "根据人物资料与页面目标，自主确定合适且有辨识度的设计方向。")
            ),
            policy(language),
            assets_prompt(page_info),
            reference_prompt(page_references(profile, feedback or "", page_info), language),
            _generation_guidance(language),
            task_template.format(page_info=_page_info_text(page_info)),
            framework_instruction(css_frame, language),
        )
        if part
    )
