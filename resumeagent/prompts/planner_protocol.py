"""Prompt-only documentation of the existing page contract, not a new validator.

Evidence: Filesystem.validate_page_spec/validate_plan/page_paths, Generator and
Refiner message builders, Planner.complete_page, assets_prompt, Runtime/State/GUI.
"""
from copy import deepcopy
import json

PROTOCOL_VERSION = 'planner-protocol-v3'


def output_contract(language='en'):
    if language == 'zh':
        return '''【输出协议：必须遵守】
只输出一个 designed_pages 标签对，准确写法见末尾完整示例。标签内是非空 JSON 数组，每项为页面对象；标签外不得有解释、总结或其他文字。禁止 Markdown 代码围栏（包括 json/python），禁止 Python 字典、注释、尾随逗号、NaN、Infinity 和省略号。字段名及字符串用标准双引号，布尔值用 true/false。字符串内换行、双引号和反斜杠必须按 JSON 规则转义。不得输出“页面规格对象”等占位符，不得再包一层 pages 对象；不要输出两段示例或两套标签，extract 会把多段拼接后交给 json.loads。

【当前代码的真实字段契约】
Validator 的最小要求不是完整业务模板：它只强制每项是 object、html_name 合法；css_name 有有效值时也要合法，并检查页面名重复。以下其他字段并非 Validator 的硬性必需，但用于完整设计、参考图、补全、导航或素材功能；本次新规划应按示例输出完整业务字段，旧的最小规格仍然有效。不要增加无用途的 id、title、sections、design_brief、USER_FACTS 等页面字段。
- html_name: string；校验必需。非空、相对路径、后缀 .html；不可为绝对路径、不可有盘符或 .. 路径段。允许安全子目录；生成器/文件系统/状态/预览用它定位网页。全站按斜杠归一化和大小写折叠后不能重复。
- css_name: string；校验器可选，原生 CSS 模式的 page_paths 必需且非空、后缀 .css，路径限制同 html_name。使用 Tailwind/Bootstrap/Materialize/Bulma 时应省略，Planner 本来就会删除它；不能输出 null、空字符串或 HTML 文件名。多页原生 CSS 给每页独立 CSS 文件，防止并发覆盖。
- description: string；校验器可选，详细设计规格。作为 page_info 原样送给 Generator/Refiner，不是代码硬解析的 sections 对象；新规划应完整提供。
- page_style: string；校验器可选，共享设计系统及本页构图。共享 brief 会追加到此字符串并持久化，Generator 从其前缀复用参考；不要改为嵌套对象或另设 design_brief 字段。
- is_main_page: boolean；可选，缺省 false。控制 Generator/Refiner 是否附带用户参考图；新规划明确写 true/false，仅 index.html 为 true，不能用字符串 "false"。
- js_description: string；可选，传给模型的交互说明，不是单独 JS 文件或待执行代码；无需额外 JS 时用空字符串。
- practice_features: string；可选，传给模型的实用功能/可访问性说明；没有额外要求可为空字符串。
- additional_features: string；可选，传给模型的有用补充；没有则为空字符串，不制造装饰功能。
- relationship: object；校验器及基本生成不强制，但 Complete Page 会直接读取它；为保留完整交互功能，新规划总是提供此对象及 buttons、links 两个数组，没有条目时用 []，不能序列化成字符串。
  - buttons: array<object>；页面补全追加入口时使用。每项的 button_name:string 是可见文案，jump_page:string 是准确目标。
  - links: array<object>；传给模型用于导航。每项的 link_name:string 是文案，jump_page:string 是准确目标。不得用 text/href 替代这些既有键。
  - imgs: array<object>；可选，仅实际提供本地素材时使用。每项 src:string 是清单中的原路径（assets_prompt 会读取），alt:string 是客观替代文本，description:string 是给模型的图片用途。未选图片用 [] 或省略；不要从参考截图发明素材。
导航目标必须是实际规划的 html_name、该文件中明确要求生成的 #id，或 USER FACTS 中已有的外部 URL。锚点优先写为 文件.html#id，所有页面可达并能回首页。这里对导航、首页标记和字段类型的要求是完整功能的输出约定，不能误称原 Validator 已检查它们。
在输出前自行核对：唯一首页、真实文件名、JSON 类型、完整业务字段、跨页链接、事实覆盖和本页专属构图。不要把核对过程输出。'''
    return '''OUTPUT PROTOCOL — MANDATORY
Return exactly one designed_pages tag pair, spelled as in the complete example at the end. Inside is a nonempty JSON array of page objects; no explanation, summary or text outside. No Markdown code fences (including json/python), Python dictionaries, comments, trailing commas, NaN, Infinity or ellipses. Use standard double quotes for keys/strings and true/false for booleans. Escape newlines, quotes and backslashes inside JSON strings. No “page specification objects” placeholders and no wrapping pages object. Do not output two examples or two tag pairs: extract concatenates multiple payloads before json.loads.

ACTUAL EXISTING FIELD CONTRACT
The validator minimum is not the full business template: it checks each item is an object with a valid html_name, validates css_name when it has a value, and rejects duplicate page names. The other fields below are not mandatory to that validator, but serve design, reference images, completion, navigation or assets. Emit the complete business fields in new plans as demonstrated; legacy minimal specifications remain valid. Do not invent unused page keys such as id, title, sections, design_brief or USER_FACTS.
- html_name: string; validator-required. Nonempty relative path ending in .html; no absolute path, drive prefix or .. path segment. Safe subdirectories are supported. Generator/filesystem/state/preview use it to locate HTML. Unique after slash normalization and case folding.
- css_name: string; optional to the validator but required and nonempty by page_paths in native CSS mode; suffix .css and the same path restrictions. Omit it for Tailwind/Bootstrap/Materialize/Bulma: Planner already removes it there. No null, empty string or HTML filename. Give native-CSS pages distinct CSS files to avoid concurrent overwrites.
- description: string; validator-optional, detailed design specification. Passed intact in page_info to Generator/Refiner, not a parsed sections object. Always supply it in new plans.
- page_style: string; validator-optional, shared design system plus page composition. The shared brief is prepended here and persisted; Generator reuses references from its prefix. Do not replace it with an object or a separate design_brief field.
- is_main_page: boolean; optional, default false. Selects whether Generator/Refiner attach the user's reference image. Explicitly emit true/false in new plans, true only for index.html, never the string "false".
- js_description: string; optional, model-readable behavior description, not an executable script or separate JS file. Empty string when no extra JavaScript is needed.
- practice_features: string; optional, model-readable usability/accessibility requirements. Empty string if there is nothing extra.
- additional_features: string; optional, model-readable useful additions. Empty string if absent; never manufacture decorative features.
- relationship: object; not required by the validator or basic generation, but Complete Page reads it directly. For full interactive compatibility always provide it with buttons and links arrays in new plans; use [] for no items, never a serialized string.
  - buttons: array<object>; appended by page completion. Each item has button_name:string for visible copy and jump_page:string for its exact destination.
  - links: array<object>; passed to the model for navigation. Each item has link_name:string and jump_page:string. Do not substitute text/href for existing keys.
  - imgs: array<object>; optional, only for actually supplied local assets. Each src:string is an exact supplied path (read by assets_prompt), alt:string is objective alternative text and description:string explains its role to the model. Omit or use [] if none; never invent assets from the reference screenshot.
Destinations are actual planned html_name values, #ids explicitly required in those files, or external URLs already in USER FACTS. Prefer file.html#id for anchors. All pages must be reachable and return home. These navigation, homepage and type conventions preserve full functionality; do not claim the existing validator enforces them.
Before responding, silently check the unique home, real filenames, JSON types, complete business fields, cross-page links, coverage of supplied facts and page-specific composition. Do not output the checklist.'''


def design_quality(language='en'):
    if language == 'zh':
        return '''【设计规格深度】
description 必须是一段紧凑、具体、可直接执行的设计方案：说明页面定位和目标读者；按顺序列出本页采用的真实资料条目；决定桌面构图/网格比例/对齐/阅读宽度与区块留白；交代标题、正文、日期（仅已提供）、注释的层级与视觉重点；为内容选择编辑式栏目、时间轴（仅已有日期）、案例带、编号条目或局部色块；说明必要交互的触发、反馈、真实目标和无脚本降级；规定手机端的重排顺序、导航与触控。不同页面必须有不同的内容任务和构图，不能只替换标题。不要在 JSON 中嵌套新的描述结构或写 CSS 代码。
page_style 必须给出全站可执行的具体值：背景/正文/主色/辅助色/强调色及其角色；字体栈、标题/正文/辅助字号与行高；容器宽度、网格、间距单位、章节留白；边框、分隔线、卡片/圆角/阴影的使用条件；导航位置、标签顺序、活动状态、键盘焦点及克制的交互。每页共享同一设计系统，再追加本页构图。宽度/字号/间距是设计参数，不是可虚构的履历统计。用户明确偏好和参考图优先于自动灵感。
默认避免蓝紫大渐变、同款圆角卡片墙、机械三栏网格、重复技能胶囊、无意义统计、虚构熟练度百分比、随机 Emoji、装饰按钮和空洞大留白。允许有明确内容价值的卡片、局部色块、渐变与交互，而不是机械禁用。
USER FACTS 是履历唯一依据；示例、规划、设计要求和参考图不是事实。不得新增学校、学位、奖项、公司、职位、经历、项目技术栈/职责/结果、论文/实验、联系方式或外链。项目只有名称就只安排名称展示；资料不足时简化结构，不编造内容填空。全站必须覆盖全部已提供事实，包括每个项目名称；不把每个栏目机械拆页。'''
    return '''DESIGN SPECIFICATION DEPTH
description must be a compact, concrete, executable design brief: identify purpose/audience; list relevant supplied information items in section order; decide desktop composition/grid proportions/alignment/reading width and whitespace rhythm; define heading/body/date (only when supplied)/caption hierarchy and visual emphasis; choose editorial rails, a timeline (only with supplied dates), case-study bands, numbered rows or color fields to suit the content; specify useful interaction triggers, feedback, real targets and no-script fallbacks; explain mobile reflow order, navigation and touch targets. Different pages need different content jobs and composition, not just different titles. Keep it a string, not a new nested description schema or CSS code.
page_style must give executable site-wide values: background/text/primary/supporting/accent colors and roles; font stack, heading/body/helper scales and line-height; container width, grid, spacing unit and section rhythm; conditions for borders, separators, cards/radii/shadows; navigation placement, label order, active state, keyboard focus and restrained interaction. Share this system across pages, then append page composition. Width/type/spacing numbers are design parameters, not invented resume metrics. Explicit preferences and visual references outrank automatic inspiration.
Default away from broad blue-purple gradients, identical rounded-card walls, mechanical three-column grids, repeated skill pills, meaningless metrics, invented proficiency percentages, random emoji, decorative buttons and empty oversized whitespace. Purposeful cards, color fields, gradients and interaction remain available rather than being mechanically banned.
USER FACTS are the sole resume evidence. Examples, plans, design requests and reference screenshots are not facts. Never invent schools, degrees, awards, companies, roles, experience, project stack/responsibilities/results, papers/experiments, contacts or external URLs. Project titles alone justify title display only. Simplify sparse information rather than filling gaps. Cover every supplied fact across the site, including every project title; do not mechanically split each section into a separate page.'''


def example_pages(language='en'):
    """Complete original example for the same explicitly fictional bilingual facts."""
    zh=language=='zh'
    style=('共享系统：背景 #faf8f4、正文 #202522、主色/强调色 #315a49、辅助 #6b726d；系统无衬线字体，中文回退 Microsoft YaHei；正文17px/1.7、栏目题22px、辅助13px。容器1100px、12栏、24px栏距、8px间距单位，章节64px、手机32px；仅用细线分隔资料，不用卡片墙。顶部同序文字导航“首页 / 项目”，当前页下划线、键盘焦点可见。'
           if zh else 'Shared system: background #faf8f4, text #202522, primary/accent #315a49, supporting #6b726d; system sans with Microsoft YaHei CJK fallback; body 17px/1.7, section headings 22px, helper 13px. Container 1100px, 12 columns, 24px gutters, 8px spacing unit; sections 64px, mobile 32px. Thin rules separate information, no card wall. Top text navigation Home / Projects in the same order, current-page underline and visible keyboard focus.')
    navigation=[{'link_name':'首页' if zh else 'Home','jump_page':'index.html'},
                {'link_name':'项目' if zh else 'Projects','jump_page':'projects.html'}]
    pages=[{
        'html_name':'index.html','css_name':'index.css','js_description':'',
        'description':('定位与读者：向研究同行和潜在合作者介绍张三（人工智能方向硕士研究生）。顺序：身份首屏→研究方向→项目入口→技能索引。桌面12栏：首屏左4栏姓名/身份，右8栏列出大语言模型、智能体系统、自动化决策；姓名48px为焦点，正文17px，辅助身份13px，左对齐且阅读宽度约65ch。研究内容采用开放文字和细线分隔，不补论文或研究结果。项目区只展示“个人主页生成系统”“多智能体执行框架”两个名称，并用 projects.html 的真实入口阅读全文；不从技能推断项目实现或完成状态。技能索引完整列出 Python、PyTorch、Transformer、RAG、Agent、Selenium、HTML、CSS，不设置熟练度。章节留白64px，有内容处不堆大空区。手机单列，先身份再研究/项目/技能，姓名缩为36px、导航可换行、触控目标至少44px。普通链接无需 JavaScript；焦点和当前页状态清楚。'
                       if zh else 'Purpose/audience: introduce Zhang San, an AI masters student, to research peers and potential collaborators. Order: identity opening, research focus, project entrances, skills index. Desktop 12-column composition: name/role in 4 columns, large language models, agent systems and automated decision-making in 8; name 48px as focal point, body 17px, supporting role 13px, left aligned with approximately 65ch reading width. Research uses open typography and thin rules, without papers or research results. Show only the supplied project titles Personal Homepage Generator and Multi-agent Execution Framework, linking to projects.html; infer neither implementation nor completion from skills. List Python, PyTorch, Transformer, RAG, Agent, Selenium, HTML and CSS without proficiency. Section spacing 64px without empty oversized regions. Mobile: identity, research, projects, skills in one column; name 36px, wrapping navigation, touch targets at least 44px. Ordinary links work without JavaScript and have clear focus/current-page states.'),
        'relationship':{'buttons':[],'links':deepcopy(navigation)},
        'practice_features':'语义化标题、键盘导航、响应式阅读。' if zh else 'Semantic headings, keyboard navigation and responsive reading.',
        'additional_features':'','page_style':style+('本页：非对称身份首屏、开放式研究栏目、纯文字技能索引。' if zh else 'Page: asymmetric identity opening, open research rail, plain text skills index.'),
        'is_main_page':True,
    },{
        'html_name':'projects.html','css_name':'projects.css','js_description':'',
        'description':('定位与读者：让希望了解张三项目经历的访问者迅速辨认两个已有项目。顺序：紧凑页标题→编号01“个人主页生成系统”→编号02“多智能体执行框架”→回首页。桌面每条用左2栏编号和右10栏项目名，名称28px，编号与标题基线对齐；用细分隔线与48px条目留白组织，不使用首页式首屏或重复两列卡片。资料只有项目名，因此不添加技术栈、年份、职责、实现、截图或成果，也不放“待补充”等填充文案。唯一导航目标是现有 index.html / projects.html，标明当前项目页，无额外JS或无效“详情”按钮。手机编号移到标题上方，标题可换行，单列间距32px；导航保持同序可换行、点击区至少44px。'
                       if zh else 'Purpose/audience: let visitors interested in Zhang Sans project experience distinguish the two supplied projects. Order: compact page heading, 01 Personal Homepage Generator, 02 Multi-agent Execution Framework, return home. Desktop entries use 2 columns for the number and 10 for the 28px project title, aligned on their baseline; thin rules and 48px entry spacing replace home-style hero and repeated two-column cards. Only titles were supplied: add no stack, year, role, implementation, screenshot, result or coming-soon filler. Navigation targets are existing index.html/projects.html only, with current-page indication; no extra JS or empty detail buttons. On mobile the number moves above the wrapping title, with 32px spacing; navigation keeps its order, wraps and has 44px touch targets.'),
        'relationship':{'buttons':[],'links':deepcopy(navigation)},
        'practice_features':'清晰编号、真实回首页链接与移动端重排。' if zh else 'Clear numbering, real home link and mobile reflow.',
        'additional_features':'','page_style':style+('本页：紧凑标题和通栏编号条目，项目名是核心。' if zh else 'Page: compact heading and full-width numbered entries focused on project titles.'),
        'is_main_page':False,
    }]
    return pages


def example_for_framework(serialized, css_frame=None):
    """Format examples only; never mutate agent data or change public signatures."""
    value=json.loads(serialized)
    if css_frame:
        for page in value if isinstance(value,list) else [value]:
            page.pop('css_name',None)
    return json.dumps(value,ensure_ascii=False,indent=2)


def page_example_for_input(page_info, fallback, css_frame=None):
    """Edit examples keep the actual filenames/keys, including omitted CSS."""
    if isinstance(page_info,dict):
        value=deepcopy(page_info)
    else:
        try:
            value=json.loads(page_info)
        except (ValueError,TypeError):
            value=json.loads(fallback)
    if not isinstance(value,dict) or not value.get('html_name'):
        value=json.loads(fallback)
    return example_for_framework(json.dumps(value,ensure_ascii=False),css_frame)
