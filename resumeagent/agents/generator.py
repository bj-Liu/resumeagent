"""Initial HTML/CSS generation from planned page dictionaries."""
from resumeagent.utils import get_html_css_from_response, user_message
from resumeagent.prompts.generator import get_write_original_website_prompt

class Generator:
    """Generator operations sharing the HomepageDesignAgent session state."""

    def get_write_original_website_messages(self,page_info):
        img = self.task["img"] if page_info.get("is_main_page", False) else None
        basic_information = self.task["basic_information"]
        academic_achievements = self.task["academic_achievements"]
        experience = self.task["experience"]
        professional_skills = self.task["professional_skills"]
        feedback = self.user_feedback if self.user_feedback else ""
        prompt = get_write_original_website_prompt(basic_information=basic_information, academic_achievements=academic_achievements, experience=experience, professional_skills=professional_skills,img=img,page_info=page_info,css_frame=self.css_frame,feedback=feedback,language=self.language)
        return user_message(prompt, [img] if img else [])

    def write_original_website(self, page_info):
        import asyncio
        return asyncio.run(self.write_original_website_async(page_info))

    async def generate_code_async(self, page_info):
        """Generate code for Runtime and interactive page actions."""
        self.validate_page_spec(page_info)
        messages = self.get_write_original_website_messages(page_info)
        for _ in range(getattr(self, 'max_agent_attempts', 5)):
            response = await self.get_answer_async(messages=messages)
            if not response:
                raise ValueError('Empty generation response')
            html, css = get_html_css_from_response(response)
            if html and (self.css_frame or css):
                return {'html':html, 'css':css}
        raise AssertionError('Failed to get the original website.')

    async def write_original_website_async(self, page_info):
        code = await self.generate_code_async(page_info)
        await self.update_html_css_async(page_info, **code)
