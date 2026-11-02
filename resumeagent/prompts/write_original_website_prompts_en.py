"""English website-generation prompt templates.

Historical export names are retained for generator.py and legacy callers.
This module adds concrete implementation guidance; user facts and global
design/factual constraints are injected by generator.py to avoid duplication.
"""

# Role strings are retained for compatibility with legacy callers.
original_role = (
    "You are a senior personal-brand and portfolio designer as well as an expert "
    "HTML, CSS and JavaScript frontend engineer. You turn real information into "
    "distinctive, content-rich, polished and accessible personal websites."
)
Tailwind_role = (
    "You are a senior Tailwind CSS designer and frontend engineer, skilled at "
    "building refined, responsive personal websites with a clear visual hierarchy."
)
Boostrap_role = (
    "You are a senior Bootstrap designer and frontend engineer. Build a distinctive "
    "personal website without falling back to an unmodified framework template."
)
Materialize_role = (
    "You are a senior Materialize CSS designer and frontend engineer, skilled at "
    "building readable, polished and responsive personal websites."
)
Bulma_role = (
    "You are a senior Bulma designer and frontend engineer, skilled at building "
    "lightweight, flexible personal websites with mature typography and layout."
)

text_task = """
WEBSITE IMPLEMENTATION TASK
Turn the page specification below into a real, runnable webpage. Do not re-plan the entire website and do not return a page outline.

PAGE SPECIFICATION (content, layout, visual and relationship requirements):
{page_info}

Implementation requirements:

1. Execute the page specification accurately
- Identify the page purpose, audience, content sections, reading order and key information before writing code.
- Treat `description` as the page-specific implementation brief and `page_style` as the shared design system plus page-specific composition. Implement both; do not follow only one field.
- Do not compress the specification into a few headings. Turn supplied facts into complete, readable and well-organized webpage content.
- Explicit user feedback outranks generic suggestions. If a page composition needs adjustment to fit the shared design system, preserve the shared visual language and adapt the layout.

2. Deliver a deliberate visual result
- Establish a clear focal point, stable grid, sensible maximum reading width and intentional spacing rhythm.
- Build hierarchy through type scale, weight, line-height, alignment, whitespace, rules and selective color. Do not put every item into an identical card.
- Choose presentation patterns that fit the content: education may use a timeline or compact record rows; experience can distinguish organization, role, date and contribution; projects can use case-study layouts; skills can be grouped by domain; research outputs can emphasize only supplied titles, authors and status.
- Purposeful color fields, soft gradients, CSS geometry, subtle textures, icons, hover states and scroll motion are welcome when they support the subject or usability.
- Avoid generic AI website patterns: full-page blue-purple gradients, identical rounded cards for every section, repetitive pill labels, skill percentage meters, invented statistics, random emoji and meaningless decorative buttons.
- Do not make the page empty in the name of minimalism or cluttered in the name of richness. Richness should come from the organization of real information, typography and visual storytelling.

3. Make the content complete, not merely scaffolded
- Present all important information required by this page specification. Organize longer material with meaningful groups, lists, timelines or expandable details, but keep important information discoverable by default.
- You may polish supplied wording for web readability. Never invent responsibilities, project context, technology stacks, research results, metrics, awards, dates or contact details.
- Do not automatically assign a listed skill to a particular project. Do not present a research interest as a completed research result. Do not invent university or company logos based on names.
- If no portrait or image asset is available, do not generate a fake avatar, random portrait or image placeholder. Use typography, CSS details or whitespace to create visual focus.

4. Interaction and frontend implementation
- Navigation, buttons and links must use real destinations from the page specification. Internal links must point to exact filenames or anchors; external links may only use URLs supplied by the user.
- Every button must have a real purpose. Do not add buttons when none are needed, and do not use `href="#"` as a fake link.
- Use JavaScript only for meaningful interactions such as mobile navigation, section navigation, back-to-top, copying a supplied contact detail or expanding content. Avoid motion added only for spectacle.
- Use semantic HTML, maintainable CSS, clear class names and CSS variables. Avoid global selector pollution and duplicate rules.
- Design desktop and mobile deliberately. Recompose grids, navigation and text widths for mobile; prevent horizontal overflow, tiny type and cramped controls.
- Keep main content visible without waiting for animation or JavaScript. Provide visible keyboard focus, sufficient contrast and respect `prefers-reduced-motion`.

5. Deliverable quality
- Return complete code, not a structural example, pseudocode, TODOs or omitted sections.
- The page must be ready to save under the specified filename and open in a browser.
- Preserve filenames, navigation targets and exact local image paths from the page specification.
- Follow the required output format exactly. Do not place explanations outside code blocks.
"""

text_img_task = """
REFERENCE SCREENSHOT AND PAGE IMPLEMENTATION
The image above is a user-provided visual reference. Learn useful design characteristics such as composition, proportions, typography hierarchy, grid, whitespace, color relationships, image treatment and visible interaction cues. Do not copy the entire website.

PAGE SPECIFICATION:
{page_info}

Rules:
- User facts and the page specification determine WHAT to present; the screenshot only informs HOW to present it.
- Do not copy the reference site's brand, logo, copy, people, schools, companies, awards, project details or contact information.
- Do not add a section or personal fact merely because it appears in the reference screenshot.
- You may learn from asymmetric layouts, sidebars, timelines, editorial grids, title proportions, color fields or whitespace, but recompose them for the current content.
- Explicit user design feedback outranks the screenshot.
- Preserve factual completeness, working navigation and exact local image paths while producing a runnable responsive page.
- Do not merely reproduce the screenshot. Apply its useful design ideas to a new page suited to this person's information.
"""

img_task = """
VISUAL-REFERENCE-ONLY WEBSITE TASK
The image above is only a visual design reference. Extract observable composition, layout proportions, typography hierarchy, colors, whitespace, borders, shadows, image treatment and visible interaction cues.

CURRENT PAGE SPECIFICATION:
{page_info}

No personal resume facts are available in this generation context:
- Use only explicit content in the page specification; do not infer identity or biography from the screenshot.
- Do not copy names, text, schools, companies, awards, projects, contact details, logos or images from the screenshot.
- Do not invent profile information to fill the page. If the page specification also lacks content, use an honest structural presentation rather than fake data.
- Borrow visual methods only and recompose them for the current page.
"""

original_output_format = """
{feedback}

Return the complete HTML and CSS. Embed any necessary JavaScript in the HTML.
Use exactly this format and add no explanation:

HTML:
```html
complete HTML document
```

CSS:
```css
complete CSS stylesheet
```
"""

Tailwind_output_format = """
{feedback}

Return a complete, runnable HTML document using the Tailwind CSS version specified by the project.
Follow the project's existing dependency-injection approach; do not introduce an incompatible or obsolete CDN.
Put necessary custom CSS in a style element and JavaScript in a script element.
Return one html code block only, with no explanation.
"""

Boostrap_output_format = """
{feedback}

Return a complete, runnable HTML document using the Bootstrap version specified by the project.
Preserve the project's existing dependency approach and do not load a conflicting duplicate version.
Put necessary custom CSS in a style element and JavaScript in a script element.
Return one html code block only, with no explanation.
"""

Materialize_output_format = """
{feedback}

Return a complete, runnable HTML document using the Materialize version specified by the project.
Preserve the existing dependency approach and do not load a conflicting duplicate version.
Put necessary custom CSS in a style element and JavaScript in a script element.
Return one html code block only, with no explanation.
"""

Bulma_output_format = """
{feedback}

Return a complete, runnable HTML document using the Bulma version specified by the project.
Preserve the existing dependency approach and do not load a conflicting duplicate version.
Put necessary custom CSS in a style element and JavaScript in a script element.
Return one html code block only, with no explanation.
"""

write_original_prompt = """
{role}

{task}

{output_format}
"""
