original_role = "您是一位专家级的Html开发者，擅长使用HTML、CSS和JavaScript编写网页。(无需输出js文件，将js文件嵌入到html文件中)"

Tailwind_role = "您是一位专家级的Tailwind开发者，擅长使用Tailwind CSS框架编写网页。"

Boostrap_role = "您是一位专家级的Bootstrap开发者，擅长使用Bootstrap CSS框架编写网页。"

Materialize_role = "您是一位专家级的Materialize开发者，擅长使用Materialize CSS框架编写网页。"

Bulma_role = "您是一位专家级的Bulma开发者，擅长使用Bulma CSS框架编写网页。"

img_task = """
上图是我们提供给您的网页的截图。
页面信息如下:{page_info}(button和link的跳转页面的文件名为其链接地址);
您的任务是根据截图和页面关系构建一个单页面应用。
- 确保您创建的页面与截图完全相同。
- 注意页面的布局，相关文本，按钮，链接等要与截图一致。
- 注意背景颜色、文字颜色、字体大小、字体系列、内边距、外边距、边框等。完全匹配颜色和大小要与截图一致。
- 使用截图中的确切文本。
- 注意，不要让图片遮挡住文字，文字的图层应该是最顶层的。
- 对于图像，尽量使用页面信息里的本地图片而且不要修改它的文件路径。
- 避免使用图像作为背景。例如: background: url('https://placehold.co/1600x900')。 你可以使用渐变的颜色作为背景或者本地图片作为背景。
- 您必须确保您生成的页面与我们提供的页面完全一致(布局、格式、文本、内容)!
- 请你严格关注图片的尺寸问题，确保最后页面的呈现效果美观。
- 鼓励您通过实现额外的JavaScript操作功能来增强网页的互动性和功能性（例如：滚动、点击、悬停，颜色变化，点击特效，页面切换等）。保证最终页面美观、信息完整、可用性良好。
"""

text_img_task = """
上图是我们提供给您的参考网页的截图。
页面信息如下:{page_info}(button和link的跳转页面的文件名为其链接地址);
您的任务是根据参考网页的结构和布局以及提供的页面信息构建一个新的网页。
- 请根据已知信息进行修改，避免虚构内容！
- 不要匹配参考网页上的文本! 
- 不需要与参考网页一致，只需学习其优点。
- 请注意背景颜色、文字颜色、字体大小、字体系列、内边距、外边距、边框等。
- 注意，不要让图片遮挡住文字，文字的图层应该是最顶层的。
- 对于图像，尽量使用页面信息里的本地图片而且不要修改它的文件路径。
- 请你严格关注图片的尺寸问题，确保最后页面的呈现效果美观。
- 尽量使页面看起来丰富，注意协调，个人主页应设计简洁。
- 避免使用图像作为背景。例如: background: url('https://placehold.co/1600x900')。 你可以使用渐变的颜色作为背景或者本地图片作为背景。
- 鼓励您使用更多颜色、更多按钮、更精致的布局，并尝试添加更多特效，例如波浪效果、渐变效果、滚动效果等。
- 鼓励您通过实现额外的JavaScript操作功能来增强网页的互动性和功能性（例如：滚动、点击、悬停，颜色变化，点击特效，页面切换等）。保证最终页面美观、信息完整、可用性良好。
"""

text_task = """
页面信息如下:{page_info}(button和link的跳转页面的文件名为其链接地址);
您的任务是根据页面信息构建一个单页面应用。
- 请注意背景颜色、文字颜色、字体大小、字体系列、内边距、外边距、边框等。
- 注意，不要让图片遮挡住文字，文字的图层应该是最顶层的。
- 对于图像，尽量使用页面信息里的本地图片而且不要修改它的文件路径。
- 尽量使页面看起来丰富，注意协调，个人主页应设计简洁。
- 鼓励您使用更多颜色、更多按钮、更精致的布局，并尝试添加更多特效，例如波浪效果、渐变效果、滚动效果等。
- 请你严格关注图片的尺寸问题，确保最后页面的呈现效果美观。
- 避免使用图像作为背景。例如: background: url('https://placehold.co/1600x900')。 你可以使用渐变的颜色作为背景或者本地图片作为背景。
- 鼓励您通过实现额外的JavaScript操作功能来增强网页的互动性和功能性（例如：滚动、点击、悬停，颜色变化，点击特效，页面切换等）。保证最终页面美观、信息完整、可用性良好。
"""

original_output_format = """
{feedback}

请输出html(包含js代码)，css代码。
"""

Tailwind_output_format = """
{feedback}

现在输出带有Tailwind CSS框架的HTML代码。(务必添加：<link href="https://cdn.jsdelivr.net/npm/tailwindcss@latest/dist/tailwind.min.css" rel="stylesheet"> 到你的html文件中。并且网站内容需要是中文)
"""

Boostrap_output_format = """
{feedback}

现在输出带有Bootstrap CSS框架的HTML代码。(务必添加：<link href="https://cdn.jsdelivr.net/npm/bootstrap@latest/dist/css/bootstrap.min.css" rel="stylesheet"> 到你的html文件中。并且网站内容需要是中文)
"""

Materialize_output_format = """
{feedback}

现在输出带有Materialize CSS框架的HTML代码。(务必添加：<link href="https://cdn.jsdelivr.net/npm/materialize-css@latest/dist/css/materialize.min.css" rel="stylesheet"> 到你的html文件中。并且网站内容需要是中文)
"""

Bulma_output_format = """
{feedback}

现在输出带有Bulma CSS框架的HTML代码。(务必添加：<link href="https://cdn.jsdelivr.net/npm/bulma@latest/dist/css/bulma.min.css" rel="stylesheet"> 到你的html文件中。并且网站内容需要是中文)
"""



write_original_prompt = """
{role}
{task}
{output_format}
"""


