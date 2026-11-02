"""中文 Planner 规格模板。

这些示例只定义数据结构和描述粒度，不是用户事实，也不是固定视觉模板。
保留现有 schema 键名，避免影响页面规划解析与后续 Generator。
"""
import json
from .planner_protocol import example_pages, output_contract, design_quality


_pages = example_pages('zh')
_example = _pages[0]
original_page_example = json.dumps(_example, ensure_ascii=False, indent=2)
original_page_template = json.dumps(_pages, ensure_ascii=False, indent=2)
_local = json.loads(original_page_example)
_local["relationship"]["imgs"] = []
_local_pages = json.loads(original_page_template)
for _page in _local_pages:
    _page["relationship"]["imgs"] = []
local_img_storage_page_example = json.dumps(_local, ensure_ascii=False, indent=2)
local_img_storage_page_template = json.dumps(_local_pages, ensure_ascii=False, indent=2)

plan_output_format_prompt = output_contract('zh') + "\n\n" + design_quality('zh') + """
以下完整合法示例仅用于学习结构与设计粒度，不是用户履历。示例虚构资料：张三，人工智能方向硕士研究生；研究方向为大语言模型、智能体系统、自动化决策；项目仅有“个人主页生成系统”和“多智能体执行框架”两个名称；技能为 Python、PyTorch、Transformer、RAG、Agent、Selenium、HTML、CSS。真实输出必须替换为 USER FACTS，不照抄示例。
<designed_pages>
{page_template}
</designed_pages>
"""

plan_output_format_prompt_local_img = plan_output_format_prompt + """
【本地图片资源】
以下是系统实际提供的本地图片信息：
{local_img_storage}
只允许选择与当前页面内容相关的图片；在 `relationship.imgs` 中使用原始路径，不能改名、拼接或虚构路径。为每张图片写准确的 alt 和用途说明。不要把参考截图当成本地图片资源。
"""


refine_page_prompt = """
你是一位资深个人主页信息架构师与视觉设计师。当前任务是把已有页面规格深化为 Generator 可以直接执行的设计方案，而不是缩短描述。

【修改目标】
- 检查当前 description 是否真正说明了页面目标、内容区块、展示顺序、信息层级、构图、重点呈现、移动端重排和交互。
- 如果描述只有“展示个人信息/项目/技能”等摘要，应补充具体组织方式和视觉决策。
- 将已提供的资料充分组织到页面中；允许改善表达、分组、摘要和呈现顺序，不允许添加任何未提供的履历事实。
- 保留全站共享设计系统，同时让本页构图适配内容，不要把所有页面改成相同卡片布局。
- 用户反馈优先级最高；明确的设计要求必须落实到具体页面结构和视觉选择中。

【严格保持】
不得修改 `html_name`、`css_name`、`relationship` 的键名和已有目标，不得新增页面或链接，不得改变 schema。可以修改现有字段的值，尤其是 `description`、`page_style`、`js_description`、`practice_features` 和 `additional_features`。
不要删除已经提供的内容，也不要把设计参考中的文字或人物信息混入用户资料。

USER FACTS / SITE TASK:
{task_info}

CURRENT PAGE SPECIFICATION:
{page_info}

STRUCTURE EXAMPLE (schema only; not user content):
{page_example}

USER DESIGN FEEDBACK:
{feedback}

输出必须是完整、合法的 JSON 对象，并且只放在以下标签中：
<modified_page>
{page_example}
</modified_page>
"""

refine_page_local_img_prompt = refine_page_prompt + """
可用本地图片资源（只能使用原始路径，不能虚构或改写）：
{local_img_storage}
"""


page_complete_prompt = """
你是一位负责全站一致性的个人主页设计师。请根据其他页面和当前页面的资料，补全当前页面规格，使其信息完整、设计具体，并与全站保持协调。

【必须完成】
1. 结合 USER FACTS、其他页面规格和当前页面已有信息，识别当前页应该承担的独立内容，不重复堆叠其他页面已经完整展示的内容。
2. 将当前页的 `description` 写成可执行设计规格：页面目标、目标读者、具体内容、区块顺序、信息层级、布局构图、重点信息呈现、视觉节奏、移动端重排和交互行为。
3. `page_style` 必须沿用全站共享设计系统，同时说明本页自己的构图方式；不得自行另起一套冲突的配色、字体或导航。
4. 完整呈现当前页相关的已知事实。不得推断或编造学校、公司、职位、项目成果、论文、日期、联系方式、外部链接或图片资源。
5. 检查页面之间的导航关系。只补充真正需要的入口，目标必须是已有页面的准确 `html_name`。
6. 让页面具有足够的信息密度和设计细节，但不要为了丰富而添加无意义装饰或重复内容。

【严格约束】
保持原始 schema 键名、值类型、`html_name` 和现有有效关系；不要新增、删除或改名字段。`completed_page` 中必须是完整页面对象。`page_relationship` 只列出需要增加“跳转到当前页面”入口的已有页面，不得虚构页面。

USER FACTS / SITE TASK:
{task_info}

OTHER PAGE SPECIFICATIONS:
{other_pages_info}

CURRENT PAGE SPECIFICATION:
{page_info}

USER DESIGN FEEDBACK:
{feedback}

只按以下格式输出，不要附加解释：
<completed_page>
{page_example}
</completed_page>
<page_relationship>
[]
</page_relationship>
"""

page_complete_prompt_local_img = page_complete_prompt + """
可用本地图片资源（只能保留系统提供的原始路径）：
{local_img_storage}
"""
