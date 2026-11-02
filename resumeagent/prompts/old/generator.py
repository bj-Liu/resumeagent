"""Design-aware generation with the established HTML/CSS output protocol."""
from .design_policy import facts_prompt, assets_prompt, policy, framework_instruction
from .design_references import select_references, reference_prompt, REFERENCES


def page_references(profile, feedback, page_info):
    # A persisted site brief takes precedence over per-page selection.
    style = (page_info or {}).get('page_style', '')
    if isinstance(style, str) and style.startswith('[Design brief design-v2: '):
        names = style.split(']', 1)[0].split(': ', 1)[1].split(', ')
        valid = tuple(name for name in names if name in REFERENCES)
        if valid:
            return valid[:2]
    return select_references(profile, feedback)


def get_write_original_website_prompt(basic_information=None, academic_achievements=None, experience=None, professional_skills=None, img=None, page_info=None, css_frame=None, feedback='', language='en'):
    profile = dict(basic_information=basic_information, academic_achievements=academic_achievements,
                   experience=experience, professional_skills=professional_skills)
    if language == 'zh':
        from .write_original_website_prompts_zh import text_task, text_img_task, img_task
    else:
        from .write_original_website_prompts_en import text_task, text_img_task, img_task
    task = (text_img_task if any(profile.values()) else img_task) if img else text_task
    return '\n\n'.join([
        'You are a senior portfolio designer and frontend engineer. Design for this person and audience, not a generic product template.',
        facts_prompt(**profile),
        f'DESIGN REQUEST / 设计要求（不是履历事实）: {feedback or ""}',
        policy(language),
        assets_prompt(page_info),
        reference_prompt(page_references(profile, feedback or '', page_info), language),
        task.format(page_info=page_info),
        framework_instruction(css_frame, language),
    ])
