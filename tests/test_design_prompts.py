"""Design-v2 behavior, evidence boundaries and existing protocol compatibility."""
import asyncio
from copy import deepcopy
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

from resumeagent.main import HomepageDesignAgent
from resumeagent.prompts.design_references import REFERENCES, PROMPT_VERSION, select_references, shared_brief, apply_shared_brief
from resumeagent.prompts.design_policy import assets_prompt
from resumeagent.prompts.generator import get_write_original_website_prompt, page_references
from resumeagent.prompts.planner import get_plan_prompt, get_refine_page_prompt, get_page_complete_prompt
from resumeagent.prompts.refiner import get_refine_prompt, get_evaluation_prompt
from resumeagent.utils import get_html_css_from_response


PROFILE = dict(basic_information='张三，人工智能方向硕士研究生。', academic_achievements='研究方向：大语言模型、智能体系统、自动化决策。',
               experience='个人主页生成系统、多智能体执行框架。', professional_skills='Python、PyTorch、Transformer、RAG、Agent、Selenium、HTML、CSS。')
PAGE = dict(html_name='index.html', css_name='site.css', is_main_page=True,
            description='展示已有介绍', page_style='统一导航',
            relationship={'buttons': [], 'links': [{'link_name': '项目', 'jump_page': 'projects.html'}],
                          'imgs': [{'src': 'images/portrait.png', 'alt': '用户头像'}]})


class DesignPromptTests(unittest.TestCase):
    def test_reference_selection_is_bounded_adaptive_and_preference_first(self):
        self.assertEqual(select_references(PROFILE)[0], 'editorial-research')
        self.assertEqual(select_references(PROFILE, '采用创意设计师的作品集构图。')[0], 'creative-sequence')
        self.assertEqual(select_references(PROFILE, '不要使用创意作品集。')[0], 'editorial-research')
        self.assertEqual(select_references(PROFILE, '不要卡片，采用创意作品集构图。')[0], 'creative-sequence')
        self.assertEqual(select_references({'basic_information': 'Software engineer, building Python tools'})[0], 'developer-workbench')
        self.assertEqual(select_references({'basic_information': 'Finance manager'})[0], 'professional-narrative')
        self.assertEqual(select_references({}, 'Swiss typography')[0], 'swiss-index')
        for profile in (PROFILE, {}, {'basic_information': 'Creative designer'}):
            self.assertLessEqual(len(select_references(profile)), 2)
        self.assertEqual(len({item['layout'] for item in REFERENCES.values()}), 5)
        for item in REFERENCES.values():
            self.assertTrue(all(item.get(key) for key in ('scenario','principles','layout','hierarchy','palette','components','avoid','example')))

    def test_bilingual_framework_matrix_contains_facts_paths_and_output_protocol(self):
        original = deepcopy(PAGE)
        for language, framework, image in itertools.product(('en','zh'), ('Tailwind','Bootstrap','Boostrap','Materialize','Bulma',None), (None,'reference.png')):
            with self.subTest(language=language, framework=framework, image=image):
                prompt = get_write_original_website_prompt(**PROFILE, page_info=PAGE, css_frame=framework, language=language, img=image, feedback='Use a restrained palette')
                for fact in PROFILE.values():
                    self.assertIn(fact, prompt)
                self.assertIn('projects.html', prompt)
                self.assertIn('images/portrait.png', prompt)
                self.assertIn('```html', prompt)
                self.assertIn('lang="zh-CN"' if language=='zh' else 'lang="en"', prompt)
                self.assertLessEqual(sum(f'[{name}]' in prompt for name in REFERENCES), 2)
                self.assertNotIn('more colors, more buttons', prompt)
                # Match the current user-authored policy, retaining the factual
                # boundary instead of freezing an obsolete translation.
                self.assertIn('不能自行补写项目目标、技术实现、职责、结果或部署情况' if language=='zh'
                              else 'do not invent its goals, implementation, responsibilities, results or deployment status', prompt)
                if framework is None:
                    self.assertIn('```css', prompt)
                    self.assertIn('exact css_name specified in page_info', prompt)
                else:
                    self.assertIn('Bootstrap' if framework=='Boostrap' else framework, prompt)
                refined = get_refine_prompt(**PROFILE, page_info=PAGE, css_frame=framework, language=language,
                                            html_code='<html>current</html>', css_code='body{}',
                                            img=image, local_img_storage=['images/portrait.png'], vision=False)
                self.assertIn('<html>current</html>', refined)
                self.assertIn('images/portrait.png', refined)
                self.assertIn(PROFILE['professional_skills'], refined)
        self.assertEqual(PAGE, original)
        html, css = get_html_css_from_response('```html\n<html lang="en"></html>\n```\n```css\nbody{}\n```')
        self.assertIn('<html', html)
        self.assertEqual(css.strip(), 'body{}')

    def test_plan_edit_and_completion_keep_tags_and_structure(self):
        for language in ('en','zh'):
            for local in ([], [{'img_path':'photo.png'}]):
                prompt = get_plan_prompt(**PROFILE, language=language, local_img_storage=local, status='expert', industry='creative')
                self.assertIn('<designed_pages>', prompt)
                self.assertIn('page_style', prompt)
                self.assertIn('index.html', prompt)
                self.assertIn('link_name', prompt)
                self.assertIn('jump_page', prompt)
                self.assertIn('全部已提供事实' if language=='zh' else 'Cover every supplied fact', prompt)
                self.assertIn('<modified_page>', get_refine_page_prompt('Facts', PAGE, language=language, local_img_storage=local))
                complete = get_page_complete_prompt('Facts', 'other pages', PAGE, language=language, local_img_storage=local)
                self.assertIn('<completed_page>', complete)
                self.assertIn('<page_relationship>', complete)

    def test_asset_manifest_distinguishes_reference_screenshot_from_real_files(self):
        prompt = get_write_original_website_prompt(**PROFILE, img='reference.png', page_info={})
        self.assertIn('当前页面没有提供可直接使用的图片文件', prompt)
        self.assertIn('不要编造图片路径', prompt)
        self.assertIn('不要把参考截图当作网页图片嵌入', prompt)
        self.assertNotIn('reference.png', assets_prompt({}))
        self.assertIn('images/portrait.png', assets_prompt(PAGE))
        self.assertIn('other.png', assets_prompt(PAGE, [{'img_path':'other.png'}]))

    def test_brief_reuses_existing_field_and_round_trips_without_changing_links(self):
        ids = select_references(PROFILE)
        brief = shared_brief(ids)
        pages = [PAGE, dict(PAGE, html_name='projects.html', is_main_page=False)]
        result = apply_shared_brief(pages, brief)
        self.assertEqual(apply_shared_brief(result, brief), result)
        restored = json.loads(json.dumps(result, ensure_ascii=False))
        self.assertEqual(page_references({}, '', restored[1]), ids)
        for before, after in zip(pages, restored):
            self.assertEqual(set(before), set(after))
            self.assertEqual(before['relationship'], after['relationship'])
            self.assertTrue(after['page_style'].startswith(brief))
        self.assertEqual(PAGE['page_style'], '统一导航')

    def test_planner_persists_brief_and_passes_actual_status_industry(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = HomepageDesignAgent(save_file=directory, llm=object(), browser=MagicMock())
            agent.task.update(PROFILE)
            agent.status, agent.industry = 'expert', 'creative'
            agent.user_feedback = 'Swiss typography'
            agent.get_answer_async = AsyncMock(side_effect=[
                '<designed_pages>'+json.dumps([PAGE])+'</designed_pages>',
                '<modified_page>'+json.dumps(PAGE)+'</modified_page>'])
            pages = asyncio.run(agent.plan_async(reuse_cached=False))
            self.assertIn('status=expert, industry=creative', str(agent.get_answer_async.call_args_list[0]))
            self.assertTrue(pages[0]['page_style'].startswith(f'[Design brief {PROMPT_VERSION}: swiss-index'))
            self.assertEqual(json.loads((Path(directory)/'pages.json').read_text(encoding='utf-8')), pages)
            # Cache load must not add calls or mutate a recovered plan.
            self.assertEqual(asyncio.run(agent.plan_async()), pages)
            self.assertEqual(agent.get_answer_async.await_count, 2)
            agent.close()

    def test_visual_critic_has_source_facts_and_preserves_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = HomepageDesignAgent(save_file=directory, llm=object(), browser=MagicMock())
            agent.task.update(PROFILE)
            agent.get_answer_async = AsyncMock(return_value='<evaluation>{"needs_refinement":false,"feedback":""}</evaluation>')
            result = asyncio.run(agent.evaluate_screenshot_async(PAGE, 'actual.png'))
            self.assertEqual(result, {'needs_refinement':False, 'feedback':''})
            self.assertIn('USER_FACTS', str(agent.get_answer_async.call_args))
            self.assertIn(PROFILE['basic_information'], str(agent.get_answer_async.call_args))
            self.assertNotIn('USER_FACTS', PAGE)
            self.assertIn('One screenshot cannot prove', get_evaluation_prompt(PAGE))
            agent.close()
