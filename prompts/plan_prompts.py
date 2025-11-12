# 根据输入的任务、图片、用户反馈、语言和本地图片存储，生成用于规划网页设计的提示信息。
def get_plan_prompt(basic_information = None, academic_achievements = None, experience=None, professional_skills=None,refine_times= None,img = None ,css_frame = None,feedback = "",language = "en",status = "student",industry = "tech",local_img_storage = []):
    """Get plan prompt"""
    if status == "student":
        prompt = f"""
        Create a personal homepage for a student. 
        The page should focus on academic achievements, extracurricular activities, and career goals. 
        Include a section  competitions, core coursework, campus involvement, and academic accomplishments.
        """
    elif status == "graduate":
        prompt = f"""
        Create a professional homepage for a entry-level professional 
        The page should emphasize work experience, key skills, and career progression. 
        Include sections for Include sections for projects, internships, papers, and certifications.
        """
    elif status == "entry_level":
        prompt = f"""
        Create a personal homepage for an entry-level professional.
        The page should highlight their career start, skills acquired, and future career goals.
        Include sections for work experience, project involvement, and skill development, with a clean and modern design, with a clean and modern design.
        """
    elif status == "mid_level":
        prompt = f"""
        Create a personal homepage for a mid-level manager.
        The page should highlight their leadership skills, strategic business achievements, and team management experience.
        Include sections for key projects, team achievements, and their role in driving team success, with a professional and refined design.
        """
    elif status == "expert":
        prompt = f"""
        Create a personal homepage for an industry expert.
        The page should showcase their significant contributions to the field, innovation, and public recognition.
        Include sections for academic publications, media coverage, and industry talks, with a distinctive design that reflects their professional image.
        """
    else:
        prompt = f"""
        Create a general personal homepage. 
        The page should focus on the individual's key experiences, skills, and achievements. 
        Include customizable sections that highlight their unique background and professional journey.
        """
        
    # 根据行业生成Prompt
    if industry == "tech":
        prompt = f"""
        Create a personal homepage for a professional in the tech industry.
        The page should highlight their technical expertise, major projects, and contributions to open-source communities.
        Include sections for certifications, project demos, and a sleek, modern design that showcases their innovative capabilities.
        """
    elif industry == "creative":
        prompt = f"""
        Design a personal homepage for a creative industry professional.
        Focus on showcasing a diverse portfolio, unique artistic processes, and collaborations with prominent brands.
        The design should be visually striking and reflect their unique artistic style and creative inspiration.
        """
    elif industry == "finance":
        prompt = f"""
        Develop a professional homepage for a finance industry expert.
        Emphasize their career achievements, successful project case studies, and in-depth market insights.
        The page should convey professionalism and trustworthiness, featuring sections for certifications and client testimonials to highlight their expertise and credibility.
        """
    elif industry == "healthcare":
        prompt = f"""
        Create a personal homepage for a professional in the healthcare industry.
        Highlight their medical expertise, extensive patient care experience, and contributions to medical research.
        Include sections for certifications, published research, and a clean, professional design that reflects their passion for healthcare.
        """
    elif industry == "education":
        prompt = f"""
        Design a personal homepage for an educator.
        Focus on showcasing their teaching philosophy, student success stories, and contributions to educational programs.
        The design should be inviting and accessible, reflecting the educator's passion for student development.
        """
    elif industry == "legal":
        prompt = f"""
        Develop a personal homepage for a professional in the legal industry.
        Emphasize their legal expertise, successful case histories, and professional certifications.
        The page should be formal and authoritative, with sections for client testimonials and published legal opinions to enhance their professional image.
        """
    elif industry == "manufacturing":
        prompt = f"""
        Create a personal homepage for a professional in the manufacturing industry.
        Highlight their technical expertise, process improvements, and contributions to product development.
        Include sections for certifications, project case studies, and a clean, efficient design that showcases their industry proficiency.
        """
    elif industry == "public_service":
        prompt = f"""
        Design a personal homepage for a public service professional.
        Focus on showcasing their community impact, policy contributions, and leadership in public initiatives.
        The design should be approachable and convey a strong commitment to social responsibility.
        """
    else:
        prompt = f"""
        Create a generic personal homepage.
        Emphasize professional accomplishments and career highlights, with sections tailored to their field, ensuring the content reflects their unique characteristics.
        """

    if language == "en":
        from .plan_prompts_en import plan_output_format_prompt,original_page_template,plan_output_format_prompt_local_img,local_img_storage_page_template
        if img and (basic_information or academic_achievements or experience or professional_skills):
            prompt = (f"Your task is to determine which modules or pages we need to create to design a personal homepage for the user. The information provided can be publicly displayed, so there is no need to deliberately avoid privacy issues. Please ensure that the page content is rich. The information typically provided by the user includes the following:"
                    f"Basic Information: {basic_information}, including name, contact details, alma mater, study duration, major, degree, etc. Since this is a personal homepage for self-use, there is no need to consider sensitive information;"
                    f"Academic Achievements: {academic_achievements}, providing text content for academic achievements, such as published papers, patents (title, summary, authors, links), etc.; "
                    f"Work/Project Experience: {experience}, mainly introducing project experiences, competition experiences, and work history; "
                    f"Professional Skills: {professional_skills}; "
                    "The image above is a reference website we have provided. You need to imitate this image, but not copy it entirely; instead, design a brand new website based on the task you need to complete. Remember, you should maintain a consistent style across all pages, so be sure to describe the page_style in detail to ensure consistency between pages (by first describing a common style, then detailing the different styles for each page);"
                    "It is particularly emphasized that the information I provided must be displayed completely and correctly. The educational background does not need a separate page; it should only be displayed in the personal information section on the homepage;"
                    "Finally, the personal homepage must respect the information provided by the user. Please ensure that all user-provided information is displayed accurately and based on factual content! This is very important!")
        elif img:
            prompt = "Your task is to design which pages we should create to design the website based on the website images I provided you.Remember, you need to keep the style consistent between each web page, that is, describe the page_style in detail to ensure the consistency of style between pages (describe the commonality through a common style, and then describe the different styles of each page)"
        else:
            prompt = (f"Your task is to determine which pages we need to create to design a personal homepage for the user. The information provided can be publicly displayed, so there is no need to deliberately avoid privacy issues. Please ensure that the page content is rich. The information typically provided by the user includes the following:"
                    f"Basic Information: {basic_information}, including name, contact details, alma mater, study duration, major, degree, etc. Since this is a personal homepage for self-use, there is no need to consider sensitive information; "
                    f"Academic Achievements: {academic_achievements}, providing text content for academic achievements, such as published papers, patents (title, summary, authors, links), etc.; "
                    f"Work/Project Experience: {experience}, mainly introducing project experiences, competition experiences, and work history; "
                    f"Professional Skills: {professional_skills}; "
                    "It is particularly emphasized that the information I provided must be displayed completely and correctly, with no need to avoid personal sensitive information. The educational background does not need a separate page; it should only be displayed in the personal information section on the homepage;"
                    "Remember, you should maintain a consistent style across all pages, so be sure to describe the page_style in detail to ensure consistency between pages (by first describing a common style, then detailing the different styles for each page);"
                    "Finally, the personal homepage must respect the information provided by the user. Please ensure that all user-provided information is displayed accurately and based on factual content! This is very important!")
        feedback = f"The user's requirements on the website(Very important! You must pay extra attention to the content here and meet user's needs) is : {feedback}" if feedback else ""
    elif language == "zh":
        from .plan_prompts_zh import plan_output_format_prompt,original_page_template,plan_output_format_prompt_local_img,local_img_storage_page_template
        if img and (basic_information or academic_achievements or experience or professional_skills):
            prompt = (f"你的任务是确定我们需要创建哪些模块或页面来设计用户自用的个人主页，所提供信息均可以公开展示，因此不需要刻意规避隐私问题，尽量保证页面内容丰满，用户提供信息一般包括以下内容："
                    f"基本信息：{basic_information}，包括姓名、联系方式、毕业院校、在读时间、所学专业，学位等信息，因为是自用个人主页，无需考虑信息敏感问题;"
                    f"学术成果：{academic_achievements}，提供学术成果的文本内容，如发表论文，专利（题目，内容简介，作者，链接）等; "
                    f"工作/项目经历：{experience},主要介绍项目经历，比赛经历和工作经历; "
                    f"专业技能：{professional_skills}; "
                    "上方的图片是我们提供的参考网站。你需要根据该图片进行模仿，但不是完全照搬，而是根据你需要完成的任务设计一个全新的网站。记住，你要保持各个网页之间的风格统一，即详细描述page_style来保证页面之间的风格一致（通过一段共性style描述共性，再描述各个页面的不同style）;"
                    "特别强调，要把我提供的信息完整正确的展示上去，教育背景不需要单独一页，仅在主页个人信息部分展示一下即可;"
                    "最后，个人主页一定要尊重用户提供的信息，请根据已知信息准确且基于事实的要完整正确地展示用户提供的所有信息！这很重要！")
        elif img:
            prompt = "你的任务是确定我们需要创建哪些页面来设计基于我提供的网站图片的个人主页。(需要完全根据图片设计，尽量做到一致)。记住，你要保持各个网页之间的风格统一，即详细描述page_style来保证页面之间的风格一致（通过一段共性style描述共性，再描述各个页面的不同style）"
        else:
            prompt = (
                    f"你的任务是确定我们需要创建哪些页面来设计用户自用的的个人主页，所提供信息均可以公开展示，因此不需要刻意规避隐私问题，尽量保证页面内容丰满，用户提供信息一般包括以下内容："
                    f"基本信息：{basic_information}，包括姓名、联系方式、毕业院校、在读时间、所学专业，学位等信息，因为是自用个人主页，无需考虑信息敏感问题; "
                    f"学术成果：{academic_achievements}，提供学术成果的文本内容，如发表论文，专利（题目，内容简介，作者，链接）等; "
                    f"工作/项目经历：{experience},主要介绍项目经历，比赛经历和工作经历; "
                    f"专业技能：{professional_skills}; "
                    "特别强调，要把我提供的信息完整正确的展示上去，没有规避个人敏感信息的需要，教育背景不需要单独一页，仅在主页个人信息部分展示一下即可;"
                    "记住，你要保持各个网页之间的风格统一，即详细描述page_style来保证页面之间的风格一致（通过一段共性style描述共性，再描述各个页面的不同style）;"
                    "最后，个人主页一定要尊重用户提供的信息，请根据已知信息准确且基于事实的完整正确地展示用户提供的所有信息！这很重要！")
        feedback = f"用户对个人主页的需求(非常重要！你必须特别注意这里的内容，并满足用户的需求)是：{feedback}" if feedback else ""
    if local_img_storage:
        prompt += plan_output_format_prompt_local_img.format(local_img_storage = local_img_storage,page_template = local_img_storage_page_template)
    else:
        prompt += plan_output_format_prompt.format(page_template = original_page_template)
    return prompt

#根据输入的任务、页面信息、用户反馈、语言和本地图片存储，生成用于优化网页的提示信息。
def get_refine_page_prompt(task,page_info,css_frame = None,feedback = "",language = "en",local_img_storage = []):
    if language == "en":
        from .plan_prompts_en import refine_page_prompt,original_page_example,local_img_storage_page_example,refine_page_local_img_prompt
        task_info = f"The requirements of the website is {task}" if task else ""
        feedback = f"The user feedback on the webpage(Very important! You must pay extra attention to the content here and prioritize making modifications to it) is : {feedback}" if feedback else ""
    elif language == "zh":
        from .plan_prompts_zh import refine_page_prompt,original_page_example,local_img_storage_page_example,refine_page_local_img_prompt
        task_info = f"个人主页的需求是{task}" if task else ""
        feedback = f"用户对个人主页的反馈(非常重要！你必须特别注意这里的内容，并优先进行修改)是：{feedback}" if feedback else ""
    if local_img_storage:
        page_example = local_img_storage_page_example
        prompt = refine_page_local_img_prompt.format(task_info = task_info,page_info = page_info,page_example = page_example,feedback = feedback,local_img_storage = local_img_storage)
    else:
        page_example = original_page_example
        prompt = refine_page_prompt.format(task_info = task_info,page_info = page_info,page_example = page_example,feedback = feedback)
    return prompt

#用于生成提示信息，根据不同的语言和是否有本地图片存储来选择不同的模板格式,生成用于完成页面操作的提示信息。
def get_page_complete_prompt(task= "",other_pages_info="",page_info="",feedback = "" ,language = "en",local_img_storage = []):
    if language == "en":
        from .plan_prompts_en import page_complete_prompt,page_complete_prompt_local_img
        feedback = f"The user feedback on how to complete the webpage(Very important! You must pay extra attention to the content here and prioritize making modifications to it) is : {feedback}" if feedback else ""
        task_info = f"The requirements of the website is {task}" if task else ""
    elif language == "zh":
        from .plan_prompts_zh import page_complete_prompt,page_complete_prompt_local_img
        feedback = f"用户对如何完成个人主页的反馈(非常重要！你必须特别注意这里的内容，并优先进行修改)是：{feedback}" if feedback else ""
        task_info = f"网站的需求是{task}" if task else ""
    if local_img_storage:   #非空，使用包含本地图片存储的提示模板 
        prompt = page_complete_prompt_local_img.format(task_info = task_info,other_pages_info = other_pages_info,page_info = page_info,feedback = feedback,local_img_storage = local_img_storage)
    else:
        prompt = page_complete_prompt.format(task_info = task_info,other_pages_info = other_pages_info,page_info = page_info,feedback = feedback)
    return prompt

if __name__ == "__main__":
    print(get_plan_prompt("test",img = True))
    print(get_refine_page_prompt("test","test"))
    print(get_page_complete_prompt("test","test"))