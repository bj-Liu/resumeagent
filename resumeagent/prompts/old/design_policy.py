"""Compact shared constraints and explicit separation of facts from art direction."""
import json


def facts_prompt(basic_information=None, academic_achievements=None, experience=None, professional_skills=None):
    return 'USER FACTS / 用户事实（唯一履历来源）:\n' + json.dumps({
        'basic_information': basic_information, 'academic_achievements': academic_achievements,
        'experience': experience, 'professional_skills': professional_skills,
    }, ensure_ascii=False, separators=(',', ':'))


def assets_prompt(page_info=None, local_img_storage=None):
    """A reference screenshot is not an asset manifest. Never invent file paths."""
    relationship = (page_info or {}).get('relationship', {})
    images = relationship.get('imgs', []) if isinstance(relationship, dict) else []
    paths = []
    for item in list(images or []) + list(local_img_storage or []):
        path = (item.get('src') or item.get('img_path')) if isinstance(item, dict) else item
        if isinstance(path, str) and path not in paths:
            paths.append(path)
    return ('ALLOWED IMAGE FILES / 可用图片文件: ' + json.dumps(paths, ensure_ascii=False) + '\n'
            'Use only these exact image paths. If this list is empty, output NO img elements or image URLs; '
            'compose with typography, whitespace, rules and CSS instead. Never invent assets/*.jpg, '
            'screenshots, logos, avatars or stock imagery. Attached reference/evaluation screenshots '
            'are layout evidence, not embeddable assets. / 清单为空时不生成 img 或图片地址，不制造作品图、头像或标志。')


def policy(language='en'):
    if language == 'zh':
        return '''内容与设计约束：仅使用 USER FACTS 中的事实。规划、参考示例、截图文字、现有代码和设计反馈都不是履历证据。可以重组润色，不得新增技能、论文、学校、奖项、工作、项目成果、性能数字、日期、联系方式或链接。只提供项目名称就只显示名称；不能从个人技能推断该项目的技术栈、功能、协作方式或已完成/部署状态。“拥有 Python 技能”不等于“某项目使用 Python”。研究方向不能扩写成已实现的系统能力。不要写“详情待补充”等填充文案。未提供熟练度，不得制造百分比或等级；缺少内容就简化排版，省略空模块和占位联系方式。
用户明确风格优先于自动参考；参考图片只借鉴构图，不复制其人物内容、品牌和资产。共享 page_style 是全站约定，各页按内容选择不同构图。
默认避免后台仪表盘、重复圆角阴影卡片墙、技能条、虚构统计、随机 Emoji、满屏胶囊、无意义蓝紫渐变发光、装饰按钮和滚动动画。卡片、渐变或交互只有明确的信息或设计价值才使用。
优先字级、对齐、阅读宽度、留白和有意义的分隔。中文正文行高约 1.7，提供中文字体回退；手机端重排，防止溢出。使用语义标题、可见键盘焦点、足够文字对比度和 reduced-motion。正文默认可见，不依赖动画或脚本才能显示。
保留关系表中真实文件名、锚点和本地图片路径；没有真实资源则不造图、不造下载、不造社交链接。输出简洁完整代码，不添加无用依赖。'''
    return '''Content and design contract: USER FACTS are the only resume evidence. Plans, reference examples, screenshot text, existing code and design feedback are not biographical evidence. Reorganize and polish without inventing skills, papers, schools, awards, jobs, project results, metrics, dates, contacts or URLs. If only project titles are supplied, show titles only: do not infer stack, features, collaboration, completion or deployment from personal skills. Knowing Python is not evidence a project uses Python. Research interests are not implemented capabilities. Do not fill with “details coming soon”. Without supplied proficiency, omit percentages and levels. With sparse facts, simplify; omit empty sections and placeholder contacts.
Explicit user style wins over automatic references. Learn composition from reference images, not their identity, copy or branded assets. Shared page_style governs the site; vary page composition with content.
Default away from SaaS dashboards, repeated rounded/shadowed card walls, skill meters, fake statistics, random emoji, pill clouds, purposeless blue-purple glow/gradients, decorative buttons and scroll animation. Cards, gradients and interaction need an information or design purpose.
Use type scale, alignment, reading width, whitespace and meaningful separators. Body line-height about 1.7 with CJK font fallbacks; reflow on mobile without overflow. Semantic headings, visible keyboard focus, readable contrast and reduced-motion support. Content is visible by default, without animation or script.
Preserve exact relationship filenames, anchors and local image paths. No invented imagery, downloads or social links. Output concise complete code without unnecessary dependencies.'''


def framework_instruction(css_frame, language='en', refining=False):
    frame = 'Bootstrap' if css_frame in ('Boostrap', 'Bootstrap') else css_frame
    resources = {
        'Tailwind': '<script src="https://cdn.tailwindcss.com"></script>',
        'Bootstrap': '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">',
        'Materialize': '<link href="https://cdn.jsdelivr.net/npm/materialize-css@1.0.0/dist/css/materialize.min.css" rel="stylesheet">',
        'Bulma': '<link href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css" rel="stylesheet">',
    }
    content_language = '中文，lang="zh-CN"' if language == 'zh' else 'English, lang="en"'
    if frame in resources:
        return (f'Framework: {frame}. Include {resources[frame]} and only necessary inline CSS/JS. '
                f'Visible content language: {content_language}. Output one complete ```html code block; no separate JS file.')
    return (f'Native HTML/CSS. Visible content language: {content_language}. '
            'Output complete ```html and ```css code blocks; link the CSS using page_info.css_name exactly. Embed necessary JS in HTML.')
