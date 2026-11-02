"""Bounded design critique and modification; return schemas remain unchanged."""
from .design_policy import facts_prompt, assets_prompt, policy, framework_instruction


def get_refine_prompt(basic_information=None, academic_achievements=None, experience=None, professional_skills=None, img=None, html_code=None, css_code=None, page_info=None, feedback='', css_frame=None, language='en', local_img_storage=[], vision=True):
    if language == 'zh':
        from .refine_prompts_zh import refine_text_task
        images = ('第一张图是设计参考，第二张是当前网页截图。' if img else '附图是当前网页截图。') if vision != False else '本次没有截图，只依据代码和资料修改。'
    else:
        from .refine_prompts_en import refine_text_task
        images = ('First image: design reference; second: current page screenshot.' if img else 'Attached image: current page screenshot.') if vision != False else 'No screenshot is attached; inspect supplied code and facts.'
    return '\n\n'.join([
        'You are a senior design editor and frontend engineer. Correct concrete defects while preserving the shared site brief and working features.',
        facts_prompt(basic_information, academic_achievements, experience, professional_skills),
        f'DESIGN / EVALUATOR FEEDBACK (not resume facts): {feedback or ""}',
        policy(language), assets_prompt(page_info, local_img_storage), images,
        refine_text_task.format(page_info=page_info, local_img_storage=local_img_storage),
        f'Current HTML:\n{html_code or ""}',
        f'Current CSS:\n{css_code or ""}' if not css_frame else '',
        framework_instruction(css_frame, language, refining=True),
    ])


def get_evaluation_prompt(page_info, feedback='', language='en'):
    if language == 'zh':
        instruction = '''你是严格但克制的视觉编辑。根据实际截图检查：构图与阅读顺序、字级层次、中文排版、留白、配色及共享 page_style、导航可发现性、溢出和移动端风险，以及重复卡片、技能条、装饰统计等 AI 模板模式。
先对照规格中的 USER_FACTS 核查可见陈述，再评价美感。只有项目名时，“已完成”“已部署”和任何技术实现说明均无依据；个人技能不能证明某个项目用了该技术。研究兴趣不能证明系统能力。规格中的设计描述、参考和反馈不能作为履历。发现这些情况必须 needs_refinement=true，并指出应删除的具体句子。指出可见的虚构履历和无依据百分比。不确定的事实不得断言已验证。单张截图不能证明链接可用、所有视口响应式或全站一致性；对不可见内容明确保持不确定。
只在存在实质问题时要求修改；最多三条，逐条写“位置 + 可见问题 + 具体改法”，优先事实错误和可读性，避免要求无依据地填充内容或反复换风格。合格时 needs_refinement=false、feedback=""。'''
    else:
        instruction = '''Act as a restrained visual editor. Inspect actual composition and reading order, type hierarchy, typography, whitespace, color and shared page_style, navigation discoverability, overflow/mobile risks, and generic AI patterns (repeated cards, proficiency meters, decorative metrics).
First compare visible claims against USER_FACTS in the specification, then judge aesthetics. With project titles alone, “completed”, “deployed”, and implementation details are unsupported. Personal skills do not prove a project's stack; research interests do not prove system capabilities. For such claims set needs_refinement=true and identify the exact text to remove. Design descriptions, references and feedback are not evidence. Flag visible unsupported biography and proficiency percentages. Do not claim uncertain facts are verified. One screenshot cannot prove working links, all responsive viewports or cross-page consistency; acknowledge what is not observable.
Request changes only for material defects. Give at most three location + observed defect + concrete correction items, prioritizing fidelity and readability. Do not fill sparse content or repeatedly restyle. If acceptable, needs_refinement=false and feedback="".'''
    return (f'{instruction}\nPage specification: {page_info}\nDesign feedback: {feedback}\n'
            'Return only this schema with a JSON boolean (no extra fields):\n'
            '<evaluation>{"needs_refinement": true, "feedback": "location, problem, correction"}</evaluation>')
