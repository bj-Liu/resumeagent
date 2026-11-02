"""Prompt assembly for planning and completing personal-website page specifications.

The public function signatures and XML-like output tags are kept compatible with
the existing application. Page descriptions are deliberately detailed enough to
guide the Generator; they are not reduced to short content labels.
"""
from .design_policy import facts_prompt, policy
from .design_references import select_references, reference_prompt, shared_brief
from .planner_protocol import example_for_framework, page_example_for_input


def _is_zh(language):
    return str(language or "en").lower().startswith("zh")


def _nonempty(parts):
    return [str(part) for part in parts if part is not None and str(part).strip()]


def get_plan_prompt(
    basic_information=None,
    academic_achievements=None,
    experience=None,
    professional_skills=None,
    refine_times=None,
    img=None,
    css_frame=None,
    feedback="",
    language="en",
    status="student",
    industry="tech",
    local_img_storage=[],
):
    """Build the full planning prompt while retaining the historical API."""
    profile = {
        "basic_information": basic_information,
        "academic_achievements": academic_achievements,
        "experience": experience,
        "professional_skills": professional_skills,
    }
    zh = _is_zh(language)

    if zh:
        from .plan_prompts_zh import (
            plan_output_format_prompt,
            original_page_template,
            plan_output_format_prompt_local_img,
            local_img_storage_page_template,
        )
        planning_instruction = """
你负责为个人主页制定真正可执行的多页面设计方案，而不是给页面写目录摘要。

规划时先理解人物身份、目标读者、资料类型和内容数量，再决定页面数量与组织方式：
- 资料不多时，优先做完整、内容充实的单页主页；资料足够丰富且有清晰主题时，才拆分为多个页面。
- 不要把 About、Education、Experience、Skills 等每个栏目机械地拆成一个 HTML 文件。可以把相关内容组织在同一页面的不同区块。
- 一般个人主页应保持易浏览，避免为了显得复杂而制造过多页面；除非资料确实丰富，不要拆出大量只有几行内容的页面。
- 首页文件名必须是 index.html。每个页面都应有明确用途，不能只是重复首页内容。
- 全站必须覆盖所有用户提供的重要事实，包括每段经历、每个项目名称、每项奖项、教育信息和技能。可以合理分组、摘要和跨页组织，但不能静默丢弃。
- 没有论文时可以展示用户明确提供的研究兴趣或研究方向，但不能虚构论文、发表状态、实验结果或学术荣誉。
- 对内容较丰富的个人主页，优先考虑精选内容在首页呈现、完整内容在相应页面展开的组织方式。

最重要：每个页面的 description 都必须是 Generator 可以直接执行的详细页面设计规格，而不是“展示个人信息和项目”这样的短句。请说明页面目的、读者、内容区块、展示顺序、信息优先级、布局构图、重点内容的呈现方式、视觉层次、交互行为和移动端组织。具体细节应来自用户资料和设计需求，不要套用同一个模板。
"""
        feedback_label = "用户的设计要求（只定义网站视觉、布局和体验，不是履历事实）"
        image_note = "用户提供的截图仅用于学习布局、视觉语言和交互线索；不得把截图中的人物、学校、文字、奖项或联系方式当作用户事实。"
    else:
        from .plan_prompts_en import (
            plan_output_format_prompt,
            original_page_template,
            plan_output_format_prompt_local_img,
            local_img_storage_page_template,
        )
        planning_instruction = """
You are planning an executable personal-website design, not writing a short table of contents.

Understand the person's identity, audience, information types and content volume before choosing the page count and structure:
- For a small profile, prefer a complete, content-rich single-page homepage. Split into multiple pages only when the material has substantial, distinct themes.
- Do not mechanically create one HTML file for About, Education, Experience and Skills each. Related information can be organized as sections on one page.
- Keep the site easy to browse. Do not create many pages containing only a few lines merely to make the project look complex.
- The homepage filename must be index.html. Every page needs a distinct purpose and must not simply repeat the homepage.
- Cover all important supplied facts across the site, including every experience, project title, award, education detail and skill. You may group, summarize and distribute them, but do not silently discard them.
- If no publications are supplied, present only explicitly supplied research interests or focus areas; never invent papers, publication status, experimental results or academic honors.
- For a substantial profile, consider a homepage with selected highlights and dedicated pages/sections for the complete material.

Most importantly, each page's description must be an executable design specification for the Generator, not a short phrase such as “show profile and projects”. Explain the page purpose, audience, content modules, section order, information priority, composition, treatment of important content, visual hierarchy, useful interactions and mobile organization. Ground the details in the supplied profile and design request rather than applying one template to every person.
"""
        feedback_label = "USER DESIGN REQUEST (visual, layout and experience preferences; not resume evidence)"
        image_note = "A supplied screenshot is for learning composition, visual language and interaction cues only; its people, schools, text, awards and contact details are not user facts."

    ids = select_references(profile, feedback or "", status=status, industry=industry)
    output = (
        plan_output_format_prompt_local_img.format(
            local_img_storage=local_img_storage,
            page_template=example_for_framework(local_img_storage_page_template, css_frame),
        )
        if local_img_storage
        else plan_output_format_prompt.format(page_template=example_for_framework(original_page_template, css_frame))
    )

    return "\n\n".join(
        _nonempty(
            [
                planning_instruction,
                facts_prompt(**profile),
                f"{feedback_label}:\n{feedback or ('未提供额外设计要求。请根据资料自主形成有辨识度的设计方向。' if zh else 'No additional design request was supplied. Develop a distinctive direction from the profile.')}",
                (
                    f"Context hints only: status={status}, industry={industry}, framework={css_frame}; "
                    f"previous refinement count={refine_times}."
                ),
                policy("zh" if zh else "en"),
                reference_prompt(ids, "zh" if zh else "en"),
                (
                    "请将同一份 shared brief 放在每个 page_style 的开头，并在后面追加本页独有的构图方案。"
                    "如果用户明确指定了颜色、风格或参考截图，用户要求优先于自动参考；所有页面必须采用同一套最终设计系统，"
                    "但页面构图应根据内容变化。使用下方真实字段契约，只有 css_name 与图片数组按条件提供；不要发明新键。"
                    if zh
                    else
                    "Put the same shared brief at the beginning of every page_style, then append the page-specific composition. "
                    "Explicit user preferences and supplied reference screenshots outrank automatic references. All pages must share "
                    "the final design system, while composition varies with content. Use the actual field contract below; "
                    "css_name and image arrays are conditional. Do not invent new keys."
                ),
                shared_brief(ids, "zh" if zh else "en"),
                image_note if img else "",
                ((f'当前为框架模式 {css_frame}：示例与输出省略 css_name。' if zh else f'Framework mode {css_frame}: omit css_name in the output as in the example.')
                 if css_frame else ('当前为原生 CSS 模式：每页必须提供独立的非空 .css 文件名。' if zh else 'Native CSS mode: each page requires a distinct nonempty .css filename.')),
                output,
            ]
        )
    )


def get_refine_page_prompt(
    task,
    page_info,
    css_frame=None,
    feedback="",
    language="en",
    local_img_storage=[],
):
    """Improve a planned page specification without changing its schema or routes."""
    zh = _is_zh(language)
    if zh:
        from .plan_prompts_zh import (
            refine_page_prompt,
            original_page_example,
            local_img_storage_page_example,
            refine_page_local_img_prompt,
        )
    else:
        from .plan_prompts_en import (
            refine_page_prompt,
            original_page_example,
            local_img_storage_page_example,
            refine_page_local_img_prompt,
        )
    template = refine_page_local_img_prompt if local_img_storage else refine_page_prompt
    return (
        template.format(
            task_info=task or "",
            page_info=page_info,
            page_example=page_example_for_input(page_info, local_img_storage_page_example if local_img_storage else original_page_example, css_frame),
            feedback=feedback or "",
            local_img_storage=local_img_storage,
        )
        + "\n\n"
        + policy("zh" if zh else "en")
    )


def get_page_complete_prompt(
    task="",
    other_pages_info="",
    page_info="",
    feedback="",
    language="en",
    local_img_storage=[],
):
    """Complete an existing page specification while preserving navigation contracts."""
    zh = _is_zh(language)
    if zh:
        from .plan_prompts_zh import page_complete_prompt, page_complete_prompt_local_img, original_page_example
    else:
        from .plan_prompts_en import page_complete_prompt, page_complete_prompt_local_img, original_page_example
    template = page_complete_prompt_local_img if local_img_storage else page_complete_prompt
    return (
        template.format(
            task_info=task or "",
            other_pages_info=other_pages_info,
            page_info=page_info,
            feedback=feedback or "",
            local_img_storage=local_img_storage,
            page_example=page_example_for_input(page_info, original_page_example),
        )
        + "\n\n"
        + policy("zh" if zh else "en")
    )
