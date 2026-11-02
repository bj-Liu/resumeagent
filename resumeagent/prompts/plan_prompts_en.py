"""English Planner specification templates.

Examples define schema and the required level of detail, not user facts or a
fixed visual template. Existing schema keys are retained for compatibility.
"""
import json
from .planner_protocol import example_pages, output_contract, design_quality


_pages = example_pages('en')
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

plan_output_format_prompt = output_contract('en') + "\n\n" + design_quality('en') + """
The complete valid example below teaches structure and design specificity, not user biography. Fictional example facts: Zhang San, an AI masters student; research in large language models, agent systems and automated decision-making; only the project titles Personal Homepage Generator and Multi-agent Execution Framework; skills Python, PyTorch, Transformer, RAG, Agent, Selenium, HTML and CSS. Replace all example content with actual USER FACTS.
<designed_pages>
{page_template}
</designed_pages>
"""

plan_output_format_prompt_local_img = plan_output_format_prompt + """
AVAILABLE LOCAL IMAGE ASSETS
{local_img_storage}
Select only images relevant to the page. Preserve exact paths in `relationship.imgs`, and provide accurate alt text and a specific usage description. Never treat a reference screenshot as an available local asset.
"""


refine_page_prompt = """
You are a senior personal-website information architect and visual designer. Deepen the existing page specification into an executable design brief for the Generator; do not shorten it into a summary.

OBJECTIVES
- Check whether `description` explains the page purpose, content sections, order, information hierarchy, composition, focal content, mobile reflow and interactions.
- If it only says “show profile/projects/skills”, replace it with concrete organization and visual decisions.
- Organize supplied facts fully. You may clarify, group, summarize and reorder them, but may not add unsupported biography.
- Preserve the shared site design system while adapting this page's composition to its content. Do not force every page into identical cards.
- User feedback has priority and must be translated into concrete structural and visual decisions.

PRESERVE STRICTLY
Do not change `html_name`, `css_name`, the `relationship` keys or existing destinations. Do not add pages or links and do not change the schema. You may improve values of existing fields, especially `description`, `page_style`, `js_description`, `practice_features` and `additional_features`.
Do not remove supplied content or treat reference copy and people as user facts.

USER FACTS / SITE TASK:
{task_info}

CURRENT PAGE SPECIFICATION:
{page_info}

STRUCTURE EXAMPLE (schema only; not user content):
{page_example}

USER DESIGN FEEDBACK:
{feedback}

Return the complete valid JSON object only inside:
<modified_page>
{page_example}
</modified_page>
"""

refine_page_local_img_prompt = refine_page_prompt + """
AVAILABLE LOCAL IMAGE ASSETS (preserve exact paths; never invent or rewrite paths):
{local_img_storage}
"""


page_complete_prompt = """
You are responsible for completing this page while maintaining site-wide consistency. Use the other page specifications and current-page information to make this page complete, specific and coherent with the rest of the site.

REQUIRED WORK
1. Use USER FACTS, other page specifications and the current page to identify this page's distinct responsibility. Avoid repeating content already fully covered elsewhere.
2. Write `description` as an executable design specification: purpose, audience, concrete content, section order, information hierarchy, composition, focal content, visual rhythm, mobile reflow and useful interactions.
3. Preserve the shared site design system in `page_style` and explain this page's own composition. Do not introduce conflicting colors, typography or navigation.
4. Present all known facts relevant to this page. Never infer or invent schools, employers, roles, project outcomes, papers, dates, contact details, external links or image assets.
5. Check navigation relationships. Add only genuinely useful entrances to this page, and target exact `html_name` values of existing pages.
6. Make the page information-rich and visually considered, without adding meaningless decoration or duplicated content.

STRICT CONSTRAINTS
Preserve the original schema keys, value types, `html_name` and existing valid relationships. Do not add, remove or rename fields. `completed_page` must contain the complete page object. `page_relationship` must list only existing pages that need an entrance to the current page; never invent a page.

USER FACTS / SITE TASK:
{task_info}

OTHER PAGE SPECIFICATIONS:
{other_pages_info}

CURRENT PAGE SPECIFICATION:
{page_info}

USER DESIGN FEEDBACK:
{feedback}

Return only this format, with no explanation:
<completed_page>
{page_example}
</completed_page>
<page_relationship>
[]
</page_relationship>
"""

page_complete_prompt_local_img = page_complete_prompt + """
AVAILABLE LOCAL IMAGE ASSETS (preserve only exact supplied paths):
{local_img_storage}
"""
