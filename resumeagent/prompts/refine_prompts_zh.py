"""中文 Refiner 模板；保留旧模块导出名称以兼容现有调用。"""
from .write_original_website_prompts_zh import (
    original_role, Tailwind_role, Boostrap_role, Materialize_role, Bulma_role
)

refine_role = (
    "你是一位资深网页视觉设计师、信息架构师和前端工程师。"
    "你需要基于真实截图、页面规格、用户反馈和现有代码进行有判断力的修改。"
    "你不是为了展示创意而推翻一切，而是准确解决问题并提升完成度。"
)

refine_text_task = """
【本轮修改目标】
请先理解页面规格和当前实现，再判断哪些问题值得修改。优先级依次为：
1. 用户明确提出的反馈；
2. 页面内容是否完整、准确，是否遗漏已提供的重要事实；
3. 页面结构、阅读顺序、信息层级和导航是否清楚；
4. 字体、行距、留白、对齐、配色和视觉重心；
5. 移动端布局、溢出、可访问性和交互问题；
6. 装饰细节和动效。

【设计修改原则】
- 不要只做表面换色。若问题来自构图或信息层级，应调整真实布局、网格、区块顺序和内容呈现方式。
- 不要把所有内容重新塞进相同的圆角卡片，也不要默认增加渐变、玻璃拟态、技能进度条、装饰数字或无意义动画。
- 允许有目的地使用非对称布局、编辑式分栏、时间轴、编号条目、细线、局部色块、柔和纹理和轻量动效。
- 保持全站共享设计系统，包括颜色角色、字体、间距、导航和交互状态；除非用户明确要求改变全站风格，不要擅自另起一套。
- 保留已经正常工作的功能、真实页面路径、锚点、文件名和本地图片路径。不要为了美观破坏功能。
- 内容真实性优先于视觉填充。可以改善表达和组织，但不能编造履历、项目细节、技术栈、成果、日期、联系方式或链接。
- 如果页面本身已经满足要求，不要为了显得做了工作而大幅重写。

【页面规格】
{page_info}

【本地图片资源】只可使用实际提供的资源，并保留路径：
{local_img_storage}

请根据当前代码完成修改，不要只给建议或修改计划。
"""

refine_feedback_task = refine_text_task
refine_img_task = refine_text_task
refine_img_text_task = refine_text_task

refine_original_output_format = """
当前 HTML：
{html_code}

当前 CSS：
{css_code}

{feedback}

请输出完整、可运行的修改结果。HTML 必须保留正确的 CSS 引用和必要的内嵌 JavaScript；CSS 必须是完整样式表，不要只输出差异片段。
输出格式：
修改后的 HTML：
```html
...
```

修改后的 CSS：
```css
...
```
"""

refine_Tailwind_output_format = """
当前 Tailwind HTML：
{html_code}

{feedback}

请输出完整 HTML 文档，不要只输出片段。保留现有有效功能和框架依赖，必要 CSS 可写入 style 标签，JavaScript 写入 script 标签。
```html
...
```
"""

refine_Boostrap_output_format = """
当前 Bootstrap HTML：
{html_code}

{feedback}

请输出完整 HTML 文档，不要只输出片段。保留现有有效功能和 Bootstrap 依赖，必要 CSS 可写入 style 标签，JavaScript 写入 script 标签。
```html
...
```
"""

refine_Materialize_output_format = """
当前 Materialize HTML：
{html_code}

{feedback}

请输出完整 HTML 文档，不要只输出片段。保留现有有效功能和 Materialize 依赖，必要 CSS 可写入 style 标签，JavaScript 写入 script 标签。
```html
...
```
"""

refine_Bulma_output_format = """
当前 Bulma HTML：
{html_code}

{feedback}

请输出完整 HTML 文档，不要只输出片段。保留现有有效功能和 Bulma 依赖，必要 CSS 可写入 style 标签，JavaScript 写入 script 标签。
```html
...
```
"""

refine_prompt = "{role}\n{task}\n{output_format}"
