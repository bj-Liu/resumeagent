def get_write_original_website_prompt(basic_information = None, academic_achievements = None, experience=None, professional_skills=None,img = None,page_info = None,css_frame = None,feedback = "",language = "en"):
    if language == "en":
        from .write_original_website_prompts_en import text_img_task,text_task,img_task,write_original_prompt,Tailwind_role,Boostrap_role,Materialize_role,Bulma_role,original_role,Tailwind_output_format,Boostrap_output_format,Materialize_output_format,Bulma_output_format,original_output_format
        feedback = f"The user's requirements is as follows(very important, please pay attention to it!):{feedback}" if feedback else ""

    elif language == "zh":
        from .write_original_website_prompts_zh import text_img_task,text_task,img_task,write_original_prompt,Tailwind_role,Boostrap_role,Materialize_role,Bulma_role,original_role,Tailwind_output_format,Boostrap_output_format,Materialize_output_format,Bulma_output_format,original_output_format
        feedback = f"用户的需求如下(非常重要，请注意!):{feedback}" if feedback else ""


    if css_frame == "Tailwind":
        role = Tailwind_role
        output_format = Tailwind_output_format.format(feedback=feedback)
    elif css_frame == "Boostrap":
        role = Boostrap_role
        output_format = Boostrap_output_format.format(feedback=feedback)
    elif css_frame == "Materialize":
        role = Materialize_role
        output_format = Materialize_output_format.format(feedback=feedback)
    elif css_frame == "Bulma":
        role = Bulma_role
        output_format = Bulma_output_format.format(feedback=feedback)
    else:
        role = original_role
        output_format = original_output_format.format(feedback=feedback)
    if img and (basic_information or academic_achievements or experience or professional_skills):
        task = text_img_task.format(page_info=page_info)
        prompt = write_original_prompt.format(role=role,task=task,page_info=page_info,output_format=output_format)
    elif img:
        task = img_task.format(page_info =page_info)
        prompt = write_original_prompt.format(role=role,task=task,output_format=output_format)
    else:
        task = text_task.format(page_info =page_info)
        prompt = write_original_prompt.format(role=role,task=task,output_format=output_format)
    return prompt

'''
这个函数主要用于指导如何根据提供的文本、图片、页面信息、CSS框架以及用户反馈来编写个人主页代码

参数说明：
basic_information: 可选，提供网站的基本信息内容，包括教育背景、个人简介、成就、现任职务和背景介绍。
academic_achievements: 可选，提供学术成果的文本内容，如发表论文，专利等。
experience: 可选，提供工作和项目经历的文本内容，如工作成果、项目描述等。
professional_skills: 可选，提供专业技能的文本内容，如技术栈、语言能力、相关证书等。
img：可选，提供用于网站的图片内容。
page_info：可选，提供关于页面的额外信息。
css_frame：可选，指定使用的CSS框架，如Tailwind、Bootstrap等。
feedback：可选，提供用户反馈或额外要求。
language：指定使用哪种语言的提示，默认为英文（"en"）。

返回值：
函数返回一个字符串，该字符串包含了根据输入参数生成的用于创建原创网站的详细指令或提示。
'''