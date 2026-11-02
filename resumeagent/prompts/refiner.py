"""Page refinement and visual evaluation prompt assembly.

Public signatures and evaluation output tags are retained for compatibility.
"""
from .design_policy import facts_prompt, assets_prompt, policy, framework_instruction


def _is_zh(language):
    return str(language or "en").lower().startswith("zh")


def get_refine_prompt(
    basic_information=None,
    academic_achievements=None,
    experience=None,
    professional_skills=None,
    img=None,
    html_code=None,
    css_code=None,
    page_info=None,
    feedback="",
    css_frame=None,
    language="en",
    local_img_storage=[],
    vision=True,
):
    """Build a revision prompt; the current code and real user facts remain primary."""
    zh = _is_zh(language)
    if zh:
        from .refine_prompts_zh import refine_text_task, refine_role
        if vision is False:
            image_context = "本轮没有可用截图。请只依据页面规格、真实资料和当前代码判断，不要声称已经观察到视觉效果。"
        elif img:
            image_context = (
                "视觉输入说明：第一张图是用户提供的设计参考（若本轮确实提供），第二张图是当前网页截图。"
                "参考图只提供布局和视觉启发；当前截图用于检查实际实现。不要复制参考图中的个人资料。"
            )
        else:
            image_context = "附图是当前网页截图。请以实际可见内容为准，不推断截图之外的功能。"
        role = refine_role
        task = refine_text_task
    else:
        from .refine_prompts_en import refine_text_task, refine_role
        if vision is False:
            image_context = "No screenshot is available in this revision. Judge only from the page specification, supplied facts and current code; do not claim visual observations."
        elif img:
            image_context = (
                "Visual input: the first image is the user's design reference (if supplied in this run); "
                "the second image is the current page screenshot. Use the reference for composition and visual "
                "inspiration, and the current screenshot to inspect implementation. Do not copy personal facts from the reference."
            )
        else:
            image_context = "The attached image is the current page screenshot. Judge only what is visible; do not infer hidden functionality."
        role = refine_role
        task = refine_text_task

    return "\n\n".join(
        [
            role,
            facts_prompt(
                basic_information,
                academic_achievements,
                experience,
                professional_skills,
            ),
            (
                ("用户设计反馈 / 评估意见" if zh else "USER DESIGN FEEDBACK / EVALUATION NOTES")
                + "（不是履历事实）:\n"
                + (feedback or ("本轮没有额外反馈，请检查实质问题并保持已有设计方向。" if zh else "No additional feedback. Fix material defects while preserving the established design direction."))
            ),
            policy("zh" if zh else "en"),
            assets_prompt(page_info, local_img_storage),
            image_context,
            task.format(
                page_info=page_info,
                local_img_storage=local_img_storage,
                feedback=feedback or "",
            ),
            ("当前 HTML 代码：\n" if zh else "CURRENT HTML:\n") + (html_code or ""),
            (("当前 CSS 代码：\n" if zh else "CURRENT CSS:\n") + (css_code or "")) if not css_frame else "",
            framework_instruction(css_frame, "zh" if zh else "en", refining=True),
            (
                "只输出完整修改后的代码，不要输出解释、分析或修改计划。"
                if zh
                else "Return only the complete revised code. Do not include explanation, analysis or a change plan."
            ),
        ]
    )


def get_evaluation_prompt(page_info, feedback="", language="en"):
    """Build a restrained evaluator prompt with an unchanged machine-readable schema."""
    if _is_zh(language):
        instruction = """你是一位严格、具体、克制的网页质量评估员。你必须依据实际截图（如果提供）和页面规格评价，不要凭空推断不可见的内容。

按以下顺序检查：
1. 事实与内容：可见的个人信息是否能在 USER FACTS 中找到依据；是否遗漏规格要求展示的重要内容；是否把研究兴趣写成已实现能力；是否把个人技能误写成项目技术栈；是否凭项目名称编造项目目标、职责、实现、部署或结果。
2. 规划落实：实际页面是否执行了 description 中的页面目标、内容顺序、布局构图、信息层级和 page_style；不能只因为页面有对应标题就判定完成。
3. 视觉质量：首屏视觉焦点、布局比例、对齐、中文字体与行距、正文可读性、留白节奏、色彩关系、区块衔接、图片裁切和装饰是否服务于内容。
4. 模板化问题：是否出现重复卡片墙、技能百分比、无意义统计数字、随机 emoji、蓝紫渐变、玻璃拟态或装饰按钮等缺乏内容依据的模式。出现不代表必然失败，只有确实损害页面时才要求修改。
5. 可用性：导航是否清楚、可见控件是否有实际用途、文字对比度、键盘焦点、移动端溢出风险和响应式布局。

事实边界：
- USER FACTS 才是履历事实来源。page_style、参考网站、截图示例和用户设计反馈不是履历证据。
- 项目名称本身不能证明项目已经完成、部署或具备某种技术能力。
- 一张截图不能证明链接可用、所有页面风格一致、移动端表现正确或交互真实可用。无法观察的项目应明确保持不确定，不要当作缺陷断言。
- 不要为了让页面显得丰富而要求模型编造或填充缺失资料。

只有存在实质问题时才设置 needs_refinement=true。最多提出三条，逐条包含“页面位置 + 可观察到的问题 + 明确修改方法”，优先事实错误、内容遗漏、阅读顺序和布局问题。若页面合格，设置 needs_refinement=false 且 feedback=""。"""
    else:
        instruction = """You are a strict, specific and restrained website quality evaluator. Evaluate only from the actual screenshot (if supplied) and page specification. Do not infer invisible behavior or content.

Inspect in this order:
1. Facts and content: can visible biographical claims be traced to USER FACTS? Is important required content missing? Are research interests presented as implemented capabilities? Is a personal skill incorrectly claimed as a project's stack? Does a project title get expanded into invented goals, responsibilities, implementation, deployment or outcomes?
2. Planning fidelity: does the page implement the page purpose, section order, composition, hierarchy and page_style in `description`? Matching section headings alone is not sufficient.
3. Visual quality: first-screen focal point, layout proportions, alignment, typography and line-height, readability, whitespace rhythm, color relationships, section transitions, image crop and whether decoration serves the content.
4. Generic patterns: repeated card walls, skill percentages, meaningless metrics, random emoji, blue-purple gradients, glassmorphism or decorative buttons without content purpose. These are not automatically failures; request changes only when they materially harm the page.
5. Usability: navigation clarity, real purpose of visible controls, contrast, keyboard focus, mobile overflow risks and responsive layout.

FACTUAL BOUNDARIES
- USER FACTS are the source of biographical evidence. `page_style`, design references, screenshot examples and design feedback are not resume evidence.
- A project title alone does not prove completion, deployment or technical capabilities.
- One screenshot cannot prove links work, all pages are consistent, mobile behavior is correct or interactions function. Mark unobservable items as unknown; do not assert them as defects.
- Never ask the Generator to invent or fill missing facts just to make a page look richer.

Set needs_refinement=true only for material defects. Give at most three items, each containing “page location + observable problem + concrete correction”, prioritizing factual errors, missing required content, reading order and layout. If acceptable, set needs_refinement=false and feedback="". """
    return (
        f"{instruction}\n\n"
        f"PAGE SPECIFICATION:\n{page_info}\n\n"
        f"USER DESIGN FEEDBACK (not resume evidence):\n{feedback or ''}\n\n"
        "Return only this schema with a JSON boolean and no extra fields:\n"
        '<evaluation>{"needs_refinement": true, "feedback": "location, observed problem, concrete correction"}</evaluation>'
    )
