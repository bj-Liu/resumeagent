"""Original layout lessons, not copied websites or resume content. No model calls."""
import re

PROMPT_VERSION = 'design-v2'

# Each entry has a different composition, not merely a different accent color.
REFERENCES = {
    'editorial-research': {
        'scenario': 'Research, academic profiles; readers looking for research interests and evidence.',
        'principles': 'Evidence first; publications only when supplied; readable long-form text.',
        'layout': 'Wide editorial container; narrow section-label rail beside a reading column.',
        'hierarchy': 'Name → one-line research focus → supplied research → projects → supplied links.',
        'palette': 'Warm paper #faf8f4, ink #202522, restrained forest #315a49.',
        'components': 'Ruled publication rows, research statements, project abstracts, text navigation.',
        'avoid': 'Publication card grids, invented venues or years, academic metrics, proficiency bars.',
        'example': 'Header/name + research statement. Below a fine rule: “Research interests” in a 2/12 rail, supplied interests in 10/12. Next section uses numbered project abstracts. Mobile: rail stacks above text.',
        'zh': ('研究与学术主页；面向研究同行。以证据和阅读为核心，只有提供论文时才列论文。',
               '宽幅编辑式容器，左侧窄栏目题、右侧正文；姓名→一句研究方向→已有研究→项目→已有链接。',
               '暖纸色 #faf8f4、墨色 #202522、克制森林绿 #315a49。用细分隔线、研究陈述和项目摘要；避免论文卡片墙、虚构年份期刊、指标和熟练度条。',
               '原创布局：页首姓名与研究陈述；细线下左侧 2/12 写“研究兴趣”，右侧 10/12 展示已有方向；下一节改为编号项目摘要。手机端栏目题移到正文上方。'),
    },
    'developer-workbench': {
        'scenario': 'Builders, engineers; readers evaluating actual projects and technical work.',
        'principles': 'Show work and supplied technical decisions, not a simulated admin product.',
        'layout': 'Compact identity masthead, then alternating full-width project case-study bands.',
        'hierarchy': 'Identity → selected project → supplied context and implementation → technical index.',
        'palette': 'Pale slate #f5f7fa, charcoal #17212b, cobalt #274caa used for links only.',
        'components': 'Numbered case studies, supplied screenshots, inline stack index, real source links.',
        'avoid': 'Dashboard sidebar, KPI cards, fake terminals, made-up benchmarks and GitHub URLs.',
        'example': '01 / supplied project title occupies a narrow rail; the broad column explains only supplied work. The next project reverses text/image emphasis if an actual image exists. Skills form a plain text index, not meters.',
        'zh': ('工程师与开发者；让读者判断真实项目。展示作品和已有技术决策，不模拟后台产品。',
               '紧凑身份页眉→通栏项目案例带→已有实现说明→技术索引；项目之间变化图文重心。',
               '浅灰 #f5f7fa、炭黑 #17212b、链接钴蓝 #274caa。用编号案例、已有截图、行内技术索引；避免侧边后台、KPI 卡、假终端、虚构性能和代码链接。',
               '原创布局：窄栏“01 / 项目名”，宽栏只解释已提供的项目内容；有真实图片时下一项目改变图文重心；技能为纯文字索引，不使用仪表或进度条。'),
    },
    'swiss-index': {
        'scenario': 'Information-dense or explicitly minimal, typographic, Swiss-style portfolios.',
        'principles': 'Alignment and type carry hierarchy; whitespace separates unlike information.',
        'layout': 'Twelve-column desktop grid; asymmetric name block and numbered section index.',
        'hierarchy': 'Large name → concise introduction → numbered content rows → quiet footer.',
        'palette': 'Off-white #f7f7f2, almost-black #191919, vermilion #b93625 sparingly.',
        'components': 'Hairline dividers, aligned dates only if supplied, bold headings, text index.',
        'avoid': 'Repeated boxed panels, oversized empty hero, decorative counters and pills.',
        'example': 'Name spans columns 1–8; a small content index spans 10–12. A project row has label / supplied title / short text, aligned to the same grid. Mobile becomes a single reading column without tiny type.',
        'zh': ('信息密集或明确偏好瑞士、极简、排版的主页。用对齐、字级和留白组织内容。',
               '桌面十二栏网格、非对称姓名区与编号目录；大姓名→简介→编号内容行→轻量页脚。',
               '米白 #f7f7f2、近黑 #191919、少量朱红 #b93625。使用细线、粗体标题、文字目录；避免重复盒子、空洞巨型首屏、装饰计数与胶囊。',
               '原创布局：姓名跨 1–8 栏，10–12 栏为内容目录；项目行按“标签 / 已有标题 / 简述”严格对齐。手机合为单列，不能靠缩小文字维持桌面布局。'),
    },
    'creative-sequence': {
        'scenario': 'Creative work and explicit expressive art direction; visual portfolio audiences.',
        'principles': 'Give supplied work visual priority; expression must preserve navigation and reading.',
        'layout': 'Oversized but wrapping masthead followed by varied full-bleed/inset work sequences.',
        'hierarchy': 'Personal statement → actual work imagery or typographic work titles → captions.',
        'palette': 'Cream #fff8ec, dark brown #2c211b, burnt orange #b74825; honor user palette.',
        'components': 'Image/caption pairs when images exist, asymmetric work titles, visible text menu.',
        'avoid': 'Invented client logos, stock work passed off as personal work, scroll-jacking, hidden text.',
        'example': 'Large left-aligned name; one supplied work image occupies 8 columns with its caption offset by 2 columns. Without images, use an expressive typographic project title and short supplied description instead of fake artwork.',
        'zh': ('创意作品或明确要求表现力的主页。优先真实作品，同时保持阅读和导航。',
               '可换行的大标题→通栏与内嵌作品交替→简短图注；不把所有作品塞入相同卡片。',
               '奶油色 #fff8ec、深棕 #2c211b、焦橙 #b74825；服从用户配色。用图注组合、非对称作品题、可见菜单；避免虚构客户标志、冒充作品的图库图片、劫持滚动。',
               '原创布局：左对齐大姓名；已有作品图占八栏，图注错开两栏。没有作品图时用有表现力的项目标题与已有简述，不制造假作品。'),
    },
    'professional-narrative': {
        'scenario': 'Professional resumes, business and management; readers seeking credibility.',
        'principles': 'Trust through clear supplied experience, restrained editorial presentation.',
        'layout': 'Two-column introduction followed by a full-width experience narrative.',
        'hierarchy': 'Name and role → concise profile → supplied experience → skills → supplied contact.',
        'palette': 'Ivory #fbfaf7, navy #233342, muted teal #386c70.',
        'components': 'Experience rows, dated timeline only when dates exist, understated contact links.',
        'avoid': 'Fake testimonials, employer logos, inflated outcomes, empty download-CV buttons.',
        'example': 'Introduction takes 7/12, a small factual skills index 4/12. Experience is a vertical sequence with titles and supplied descriptions separated by whitespace. If dates or outcomes are absent, omit those columns.',
        'zh': ('履历、商业与管理主页；以可信经历为核心。用克制的编辑式展示建立信任。',
               '双栏简介→通栏经历叙事；姓名身份→简介→已有经历→技能→已有联系方式。',
               '象牙白 #fbfaf7、藏蓝 #233342、灰青 #386c70。用经历行、仅有日期时的时间线、低调联系链接；避免假评价、公司标志、夸大成果和空简历下载。',
               '原创布局：简介占 7/12，事实技能索引占 4/12；经历纵向排列，用留白分隔标题和已知说明。没有日期或业绩时直接省略对应列。'),
    },
}

KEYWORDS = {
    'editorial-research': ('research', 'academic', 'phd', 'master', '研究', '学术', '硕士', '博士', '论文'),
    'developer-workbench': ('developer', 'engineer', 'software', 'python', '开发', '工程', '项目', '编程'),
    'swiss-index': ('swiss', 'minimal', 'typograph', '瑞士', '极简', '排版', '黑白'),
    'creative-sequence': ('creative', 'designer', 'art director', 'photograph', '创意', '设计师', '摄影', '艺术'),
    'professional-narrative': ('business', 'manager', 'finance', 'consult', '管理', '商业', '金融', '咨询'),
}


def select_references(profile=None, feedback='', page_info=None, *, status='', industry=''):
    """At most two, deterministic; explicit positive preferences outrank occupation."""
    profile = profile or {}
    facts = ' '.join(str(profile.get(k) or '') for k in
                     ('basic_information', 'academic_achievements', 'experience', 'professional_skills')).lower()
    # A negative preference must not activate the style it rejects.
    preference = ' '.join(p for p in re.split(r'[，,。；;.!\n]', feedback.lower())
                          if not re.search(r'不要|避免|不采用|不使用|avoid|\bno\b|\bnot\b', p))
    page = str((page_info or {}).get('description', '')).lower()
    scores = {}
    for name, words in KEYWORDS.items():
        scores[name] = (sum(word in facts for word in words) * 3
                        + sum(word in page for word in words)
                        + sum(word in f'{status} {industry}'.lower() for word in words))
        if any(word in preference for word in words):
            scores[name] += 100
    ranked = sorted(scores, key=lambda name: -scores[name])
    if scores[ranked[0]] == 0:
        return ('professional-narrative',)
    chosen = [ranked[0]]
    if scores[ranked[1]] > 0:
        chosen.append(ranked[1])
    return tuple(chosen)


def reference_prompt(ids, language='en'):
    lines = ['Design references (original layout lessons; never resume facts):' if language == 'en'
             else '设计参考（原创布局教学示例，绝不是用户履历事实）：']
    for index, name in enumerate(ids[:2]):
        ref = REFERENCES[name]
        lines.append(f'[{name}] ' + ('Primary composition.' if index == 0 else 'Secondary lesson only; keep primary palette and site brief.'))
        if language == 'zh':
            lines.extend(ref['zh'])
        else:
            lines.extend(f'{key.title()}: {ref[key]}' for key in
                         ('scenario', 'principles', 'layout', 'hierarchy', 'palette', 'components', 'avoid', 'example'))
    return '\n'.join(lines)


def shared_brief(ids, language='en'):
    """Stored inside existing string page_style; survives all existing checkpoints."""
    ref = REFERENCES[ids[0]]
    palette = ref['palette']
    return (f'[Design brief {PROMPT_VERSION}: {", ".join(ids)}]\n'
            f'Default palette (explicit user/reference preference wins): {palette}\n'
            'Shared tokens: --bg, --ink, --accent; use the same values on every page. '
            'Type: system sans with PingFang SC / Microsoft YaHei / Noto Sans CJK SC fallbacks; '
            'body 16–18px, line-height 1.7; headings clamp(2rem,5vw,4.5rem). '
            'Spacing: 8px base, sections 72–96px desktop / 40–56px mobile, reading width 65ch, container 1120px. '
            'Navigation: identical text labels, order, placement and active-page treatment; use exact planned filenames. '
            'Home: identity and overview; research: reading rows; projects: case studies; skills: text index. '
            'Keep shared visual language while varying content composition. User preferences and supplied reference images override defaults consistently.')


def apply_shared_brief(pages, brief):
    """Do not add keys or change content, links, filenames, or callers' dictionaries."""
    from copy import deepcopy
    result = deepcopy(pages)
    for page in result:
        style = page.get('page_style', '')
        if not isinstance(style, str):
            style = str(style)
        if not style.startswith(brief):
            page['page_style'] = brief + '\nPage composition: ' + style
    return result
