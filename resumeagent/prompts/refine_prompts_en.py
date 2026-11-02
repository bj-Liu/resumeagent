"""English Refiner templates; legacy export names remain available."""
from .write_original_website_prompts_en import (
    original_role, Tailwind_role, Boostrap_role, Materialize_role, Bulma_role
)

refine_role = (
    "You are a senior web visual designer, information architect and frontend engineer. "
    "Make considered changes based on the actual screenshot, page specification, user feedback "
    "and existing code. Do not redesign everything merely to demonstrate creativity; solve "
    "the real problems and improve the finish."
)

refine_text_task = """
REVISION OBJECTIVES
Inspect the page specification and current implementation before changing anything. Prioritize:
1. Explicit user feedback.
2. Completeness and factual accuracy of supplied content.
3. Page structure, reading order, information hierarchy and navigation.
4. Typography, line-height, whitespace, alignment, color and visual focus.
5. Mobile layout, overflow, accessibility and interaction defects.
6. Decorative details and motion.

DESIGN PRINCIPLES
- Do not merely recolor the page. If the problem is composition or hierarchy, revise the actual layout, grid, section order and content treatment.
- Do not put everything into identical rounded cards or automatically add gradients, glassmorphism, skill meters, decorative metrics or meaningless animation.
- Purposeful asymmetric layouts, editorial columns, timelines, numbered rows, hairlines, restrained color fields, subtle textures and light motion are welcome.
- Preserve the shared site design system: color roles, typography, spacing, navigation and interaction states. Do not invent a new visual identity unless the user explicitly requests a site-wide change.
- Preserve working features, real page paths, anchors, filenames and exact local image paths. Do not break functionality for appearance.
- Factual integrity outranks visual filling. You may improve wording and organization, but never invent biography, project details, technology stacks, outcomes, dates, contact details or links.
- If the page already satisfies the request, do not rewrite it extensively just to appear productive.

PAGE SPECIFICATION:
{page_info}

AVAILABLE LOCAL IMAGE ASSETS (use only supplied assets and preserve exact paths):
{local_img_storage}

Revise the supplied code. Do not return advice or a plan instead of the implementation.
"""

refine_feedback_task = refine_text_task
refine_img_task = refine_text_task
refine_img_text_task = refine_text_task

refine_original_output_format = """
Current HTML:
{html_code}

Current CSS:
{css_code}

{feedback}

Return the complete, runnable result. Keep the correct stylesheet reference and required inline JavaScript in HTML. Return the full stylesheet, not a diff.
Output format:
Revised HTML:
```html
...
```

Revised CSS:
```css
...
```
"""

refine_Tailwind_output_format = """
Current Tailwind HTML:
{html_code}

{feedback}

Return the complete HTML document, not a fragment. Preserve working features and framework dependencies. Put necessary CSS in a style element and JavaScript in a script element.
```html
...
```
"""

refine_Boostrap_output_format = """
Current Bootstrap HTML:
{html_code}

{feedback}

Return the complete HTML document, not a fragment. Preserve working features and Bootstrap dependencies. Put necessary CSS in a style element and JavaScript in a script element.
```html
...
```
"""

refine_Materialize_output_format = """
Current Materialize HTML:
{html_code}

{feedback}

Return the complete HTML document, not a fragment. Preserve working features and Materialize dependencies. Put necessary CSS in a style element and JavaScript in a script element.
```html
...
```
"""

refine_Bulma_output_format = """
Current Bulma HTML:
{html_code}

{feedback}

Return the complete HTML document, not a fragment. Preserve working features and Bulma dependencies. Put necessary CSS in a style element and JavaScript in a script element.
```html
...
```
"""

refine_prompt = "{role}\n{task}\n{output_format}"
