"""Prompts for describing reference screenshots and uploaded visual assets.

The output tags are retained for compatibility with the existing image parser.
"""
process_img_en = """
Analyze the supplied image as a visual reference for a personal website. Return a concise but useful design description in BOTH Chinese and English. Focus on visual information that can guide implementation:
- overall visual direction and mood;
- page composition, grid, alignment and relative proportions;
- header/navigation placement and behavior visible in the image;
- typography hierarchy, density and reading order;
- background, dominant colors, accent colors, borders, shadows and whitespace;
- section organization, cards/rows/timeline/image treatment and distinctive details;
- visible interaction cues, if any.

Describe observable facts only. Do not infer the identity, education, employer, achievements or contact details of people in the screenshot. Do not treat screenshot text as the current user's content. Do not claim responsive behavior or hidden interactions that cannot be observed. Avoid generic praise such as “modern and beautiful”; explain what makes the composition distinctive.

Keep each language description to a compact paragraph or short structured list. Do not output analysis or any content outside these tags:
<Chinese>{Chinese visual-reference description}</Chinese>
<English>{English visual-reference description}</English>
"""

process_img_zh = """
请把上方图片作为个人主页的视觉参考进行分析，并同时输出中文和英文描述。重点提取真正能指导网页实现的视觉信息：
- 整体设计方向、气质与视觉情绪；
- 页面构图、网格、对齐方式和各区域的大致比例；
- 页眉与导航的位置、组织方式，以及截图中可见的状态；
- 字体层级、信息密度和阅读顺序；
- 背景、主色、强调色、边框、阴影和留白；
- 内容区块的组织方式，例如卡片、列表、时间轴、图文组合及有辨识度的细节；
- 图片中确实可见的交互线索。

只描述图片中可观察到的内容。不要推断人物身份、学历、雇主、成就或联系方式；不要把截图文字当作当前用户的履历资料。无法从截图判断的响应式行为或隐藏交互，不要声称已经确认。避免只说“现代、漂亮、有设计感”，应说明具体的构图和视觉特征。

每种语言控制在一个精炼段落或简短条目内。不要输出分析过程或标签以外的内容，严格使用以下格式：
<Chinese>{图片的中文视觉描述}</Chinese>
<English>{图片的英文视觉描述}</English>
"""


def get_process_img_prompt(language="en"):
    """Return the image-analysis prompt in the requested language."""
    if str(language or "en").lower().startswith("zh"):
        return process_img_zh
    return process_img_en
