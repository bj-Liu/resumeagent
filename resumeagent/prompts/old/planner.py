"""Website planning; facts and design preferences remain distinct."""
from .design_policy import facts_prompt, policy
from .design_references import select_references, reference_prompt, shared_brief


def get_plan_prompt(basic_information=None, academic_achievements=None, experience=None, professional_skills=None, refine_times=None, img=None, css_frame=None, feedback="", language="en", status="student", industry="tech", local_img_storage=[]):
    profile = dict(basic_information=basic_information, academic_achievements=academic_achievements,
                   experience=experience, professional_skills=professional_skills)
    if language == 'zh':
        from .plan_prompts_zh import plan_output_format_prompt, original_page_template, plan_output_format_prompt_local_img, local_img_storage_page_template
        instruction = '根据实际资料确定页面数量和内容：少量资料可用单页，足够独立内容才拆页；首页文件 index.html。全站规划必须覆盖全部已提供事实，包括每一个项目名称，不能因示例省略内容。缺少论文时展示研究兴趣，不编造学术成果。'
    else:
        from .plan_prompts_en import plan_output_format_prompt, original_page_template, plan_output_format_prompt_local_img, local_img_storage_page_template
        instruction = 'Choose page count from actual content: sparse profiles may use one page; split only substantial independent content. Home filename: index.html. Cover every supplied fact somewhere in the site, including every project title; the example must not cause omissions. Without publications, present research interests, not invented achievements.'
    ids = select_references(profile, feedback or '', status=status, industry=industry)
    output = (plan_output_format_prompt_local_img.format(local_img_storage=local_img_storage, page_template=local_img_storage_page_template)
              if local_img_storage else plan_output_format_prompt.format(page_template=original_page_template))
    return '\n\n'.join([
        instruction, facts_prompt(**profile),
        f'DESIGN REQUEST (not resume evidence): {feedback or ""}',
        f'Context hints only: status={status}, industry={industry}; framework={css_frame}.',
        policy(language), reference_prompt(ids, language),
        'Put this identical shared brief at the beginning of every page_style string; append page-specific composition. If user preferences or a supplied image override defaults, specify the same final colors, typography and navigation on every page. Do not add schema keys. Keep all existing keys and relationship structures.',
        shared_brief(ids, language),
        'A supplied image is a composition reference, not a source of identity, credentials or contact details.' if img else '',
        output,
    ])


def get_refine_page_prompt(task, page_info, css_frame=None, feedback="", language="en", local_img_storage=[]):
    if language == 'zh':
        from .plan_prompts_zh import refine_page_prompt, original_page_example, local_img_storage_page_example, refine_page_local_img_prompt
    else:
        from .plan_prompts_en import refine_page_prompt, original_page_example, local_img_storage_page_example, refine_page_local_img_prompt
    template = refine_page_local_img_prompt if local_img_storage else refine_page_prompt
    return template.format(task_info=task or '', page_info=page_info,
                           page_example=local_img_storage_page_example if local_img_storage else original_page_example,
                           feedback=feedback or '', local_img_storage=local_img_storage) + '\n' + policy(language)


def get_page_complete_prompt(task="", other_pages_info="", page_info="", feedback="", language="en", local_img_storage=[]):
    if language == 'zh':
        from .plan_prompts_zh import page_complete_prompt, page_complete_prompt_local_img
    else:
        from .plan_prompts_en import page_complete_prompt, page_complete_prompt_local_img
    template = page_complete_prompt_local_img if local_img_storage else page_complete_prompt
    return template.format(task_info=task or '', other_pages_info=other_pages_info, page_info=page_info,
                           feedback=feedback or '', local_img_storage=local_img_storage) + '\n' + policy(language)
