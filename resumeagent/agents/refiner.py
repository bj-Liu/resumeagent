"""Screenshot-driven multimodal refinement and user feedback application."""
import random
import re
from resumeagent.utils import extract, get_html_css_from_response, user_message
from resumeagent.prompts.refiner import get_refine_prompt, get_evaluation_prompt

class Refiner:
    """Refiner operations sharing the HomepageDesignAgent session state."""

    def get_refine_messages(self,page_info):
        img = self.task["img"] if page_info.get("is_main_page", False) else None
        basic_information = self.task["basic_information"]
        academic_achievements = self.task["academic_achievements"]
        experience = self.task["experience"]
        professional_skills = self.task["professional_skills"]
        css_frame = self.css_frame

        code = self.tools.call('filesystem.read_page', page_info=page_info).value
        html_code, css_code = code['html'], code['css']
        page_img_path = self.page_paths(page_info)["screenshot"]

        feedback = self.user_feedback if self.user_feedback else ""

        if len(self.local_img_storage) > 10:
            local_img_storage = random.sample(self.local_img_storage,10)
        else:
            local_img_storage = self.local_img_storage
        prompt = get_refine_prompt(basic_information=basic_information, academic_achievements=academic_achievements, experience=experience, professional_skills=professional_skills,img=img,html_code=html_code,css_code=css_code,feedback=feedback,page_info=page_info,css_frame=css_frame,language=self.language,local_img_storage=local_img_storage,vision=self.vision)
        images = []
        if self.vision != False:
            if img:
                images.append(img)
            images.append(page_img_path)
        return user_message(prompt, images)

    def refine(self, page_info):
        import asyncio
        return asyncio.run(self.refine_async(page_info))

    async def refine_code_async(self, page_info):
        self.validate_page_spec(page_info)
        messages = self.get_refine_messages(page_info)
        response = await self.get_answer_async(messages=messages)
        if not response:
            raise ValueError('Empty refinement response')
        html, css = get_html_css_from_response(response)
        if not html or (not self.css_frame and not css):
            raise ValueError('Invalid refinement response')
        return {'html':html, 'css':css}

    async def refine_async(self, page_info):
        code = await self.refine_code_async(page_info)
        await self.update_html_css_async(page_info, **code)

    async def evaluate_screenshot_async(self, page_info, screenshot_path):
        """Bounded visual judgment, separate from code modification."""
        import json
        # The critic needs actual evidence, not just a potentially embellished plan.
        # This is request context only; never add private fields to persisted specs.
        specification = dict(page_info, USER_FACTS={key: self.task.get(key) for key in
                             ('basic_information', 'academic_achievements', 'experience', 'professional_skills')}
                             if hasattr(self, 'task') else {})
        prompt = get_evaluation_prompt(specification, self.user_feedback or '', self.language)
        response = await self.get_answer_async(messages=user_message(prompt, [screenshot_path]))
        try:
            payload = extract(response, 'evaluation') or response.strip()
            fenced = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', payload, re.DOTALL | re.IGNORECASE)
            result = json.loads(fenced.group(1) if fenced else payload)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError('Invalid screenshot evaluation') from exc
        if not isinstance(result, dict) or type(result.get('needs_refinement')) is not bool or not isinstance(result.get('feedback', ''), str):
            raise ValueError('Invalid screenshot evaluation schema')
        return {'needs_refinement':result['needs_refinement'], 'feedback':result.get('feedback', '')[:2000]}
