"""Website structure planning, page description editing and relationship completion."""
import logging
import asyncio
import os
import json
from resumeagent.utils import wrap_func, extract, get_content_between_a_b, modify_input_dict, format_profile, user_message
from resumeagent.prompts.planner import get_plan_prompt, get_refine_page_prompt, get_page_complete_prompt
from resumeagent.prompts.design_references import select_references, shared_brief, apply_shared_brief

logger = logging.getLogger(__name__)


class Planner:
    """Planner operations sharing the HomepageDesignAgent session state."""

    def plan(self):
        return asyncio.run(self.plan_async())

    async def plan_async(self, reuse_cached=True):
        path = os.path.join(self.save_file, 'pages.json')
        if reuse_cached and self.tools.call('filesystem.exists', path=path).value:
            self.task_queue = self.tools.call('filesystem.read_json', path=path).value
            return self.task_queue
        prompt = get_plan_prompt(
            basic_information=self.task.get('basic_information'),
            academic_achievements=self.task.get('academic_achievements'),
            experience=self.task.get('experience'), professional_skills=self.task.get('professional_skills'),
            img=self.task.get('img'), css_frame=self.css_frame, feedback=self.user_feedback or '',
            language=self.language, local_img_storage=self.local_img_storage,
            status=self.status, industry=self.industry)
        messages = user_message(prompt, [self.task['img']] if self.task.get('img') else [])
        for attempt in range(getattr(self, 'max_agent_attempts', 3)):
            response = await self.get_answer_async(messages=messages)
            try:
                raw_plan = extract(response, 'designed_pages')
                pages = json.loads(raw_plan)
                self.validate_plan(pages)
                if self.css_frame:
                    for page in pages:
                        page.pop('css_name', None)
                break
            except (ValueError, TypeError, AttributeError):
                if attempt + 1 == getattr(self, 'max_agent_attempts', 3):
                    raise ValueError('Invalid website plan') from None
        brief = shared_brief(select_references(self.task, self.user_feedback or '',
                                              status=self.status, industry=self.industry), self.language)
        pages = apply_shared_brief(pages, brief)
        refined = await self.refine_pages_async(pages)
        if any(item is None for item in refined):
            raise ValueError('Page specification refinement failed')
        self.task_queue = apply_shared_brief([item[0] for item in sorted(refined, key=lambda item:item[1])], brief)
        self.validate_plan(self.task_queue)
        self.tools.call('filesystem.write_json', path=path, data=self.task_queue)
        return self.task_queue

    async def refine_pages_async(self,pages):
        tasks = []
        for i,page in enumerate(pages):
            task = self.refine_page_async(i,page)
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        return results


    def get_modified_page_from_response(self,response,page_info):
        modified_page = extract(response,"modified_page")
        if "```python" in modified_page:
            modified_page = get_content_between_a_b("```python","```",modified_page)
        if "```json" in modified_page:
            modified_page = get_content_between_a_b("```json","```",modified_page)
        modified_page = modified_page.replace("True","true").replace("False","false")
        try:
            modified_page = json.loads(modified_page)
        except:
            modified_page = modify_input_dict(modified_page)
            try:
                modified_page = json.loads(modified_page)
            except:
                logger.warning("Failed to get the modified page. Please check the format.")
                modified_page = page_info
        if self.css_frame:
            if "css_name" in modified_page:
                del modified_page["css_name"]
        return modified_page


    def _refine_page_messages(self, page_info, feedback):
        prompt = get_refine_page_prompt(
            task=format_profile(self.task), page_info=page_info, css_frame=self.css_frame,
            feedback=feedback, language=self.language, local_img_storage=self.local_img_storage,
        )
        return user_message(prompt)

    def refine_page(self, page_info, feedback=''):
        messages = self._refine_page_messages(page_info, feedback)
        response = wrap_func(self.get_answer, messages=messages, wrap_text='Refining page now...')
        if not response:
            logger.warning('Failed to get the response.')
            return
        modified_page = self.get_modified_page_from_response(response, page_info)
        logger.info('Page has been refined.')
        return modified_page

    async def refine_page_async(self, idx, page_info, feedback=''):
        messages = self._refine_page_messages(page_info, feedback)
        response = await self.get_answer_async(messages=messages)
        if not response:
            logger.warning('Failed to get the response.')
            return
        modified_page = self.get_modified_page_from_response(response, page_info)
        logger.info(f'Page {idx+1} has been refined.')
        return [modified_page, idx]

    def complete_page(self,pages,idx):
        page_info = pages[idx]
        page_info = str(page_info)
        other_pages_info = ""
        for i,page in enumerate(pages):
            if i != idx:
                other_pages_info += f"Page {i+1}: {page}\n"
        other_pages_info = modify_input_dict(other_pages_info)
        page_info = modify_input_dict(page_info)
        feedback = self.user_feedback if self.user_feedback else ""
        task = format_profile(self.task)
        prompt = get_page_complete_prompt(task = task,page_info=page_info,other_pages_info=other_pages_info,feedback=feedback,language=self.language,local_img_storage=self.local_img_storage)
        messages = user_message(prompt)
        response = wrap_func(self.get_answer, messages=messages,wrap_text="Completing page now...")
        if not response:
            logger.warning("Failed to get the response.")
            return

        complete_page = extract(response,"completed_page")
        if "```python" in complete_page:
            complete_page = get_content_between_a_b("```python","```",complete_page)
        elif "```json" in complete_page:
            complete_page = get_content_between_a_b("```json","```",complete_page)
        try:
            complete_page = json.loads(complete_page)
            relationship = complete_page["relationship"]
            if isinstance(relationship,str):
                relationship = modify_input_dict(relationship)
                relationship = json.loads(relationship)
            complete_page["relationship"] = relationship
            pages[idx] = complete_page
        except:
            logger.warning("Failed to get the completed page. Please check the format.")

        relationship = extract(response,"page_relationship")
        if "```python" in relationship:
            relationship = get_content_between_a_b("```python","```",relationship)
        elif "```json" in relationship:
            relationship = get_content_between_a_b("```json","```",relationship)
        try:
            relationship = json.loads(relationship)
            for page_relation in relationship:
                html_name = page_relation["html_name"]
                button_name = page_relation["button_name"]
                for i,page in enumerate(pages):
                    if page["html_name"] == html_name:
                        pages[i]["relationship"]["buttons"].append({"button_name": button_name,"jump_page":complete_page["html_name"]})
        except:
            logger.warning("Failed to get the relationship. Please check the format.")

        return pages
