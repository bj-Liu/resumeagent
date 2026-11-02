"""Behavioral snapshots recorded before the cleanup; no external model calls."""
import ast
import hashlib
import inspect
import itertools
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SNAPSHOT = Path(__file__).with_name('refactor_contracts.json')
PROMPT_SNAPSHOT = Path(__file__).with_name('planner_protocol_v3_contracts.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def capture_contracts():
    from resumeagent.agents.generator import Generator
    from resumeagent.agents.refiner import Refiner
    from resumeagent.main import HomepageDesignAgent
    from resumeagent.llm.client import openai_llm, qwen_llm
    from resumeagent.mcp_server import SCHEMAS
    from resumeagent.prompts.planner import get_plan_prompt, get_refine_page_prompt, get_page_complete_prompt
    from resumeagent.prompts.generator import get_write_original_website_prompt
    from resumeagent.prompts.refiner import get_refine_prompt, get_evaluation_prompt
    from resumeagent.prompts.process_img_prompts import get_process_img_prompt
    from storage.database import Database

    page = {'html_name':'index.html','css_name':'site.css','is_main_page':True,
            'description':'Example profile','relationship':{'buttons':[],'links':[]}}
    profile = dict(basic_information='Example profile', academic_achievements='Example paper',
                   experience='Example project', professional_skills='Python')
    prompts = {}
    for language, framework, image, feedback, local in itertools.product(
        ('en','zh'), ('Tailwind','Bootstrap','Boostrap','Materialize','Bulma',None),
        (None,'reference.png'), ('','Make the header blue'), ([],[{'img_path':'photo.png','description':'portrait'}])
    ):
        key = repr((language,framework,image,feedback,bool(local)))
        arguments = dict(profile,img=image,css_frame=framework,feedback=feedback,language=language)
        calls = {
            'plan':lambda:get_plan_prompt(**arguments,local_img_storage=local),
            'specification':lambda:get_refine_page_prompt('Example requirements',page,framework,feedback,language,local),
            'complete':lambda:get_page_complete_prompt('Example requirements','Other pages',page,feedback,language,local),
            'generate':lambda:get_write_original_website_prompt(**arguments,page_info=page),
            'refine':lambda:get_refine_prompt(**arguments,html_code='<html></html>',css_code='body{}',page_info=page,local_img_storage=local),
            'evaluate':lambda:get_evaluation_prompt(page,feedback,language),
            'image':lambda:get_process_img_prompt(language),
        }
        for name, call in calls.items():
            try:
                prompts[name+key] = digest(call())
            except Exception as exc:
                prompts[name+key] = {'error':type(exc).__name__}

    agent = HomepageDesignAgent(save_file=str(ROOT/'test-artifacts'/'contract-site'),llm=object(),browser=MagicMock())
    # Historical message snapshots contain a checkout-specific screenshot path.
    # Freeze only that path to its recorded value; do not regenerate snapshots
    # or relax assertions over the prompt/message content.
    original_page_paths=agent.page_paths
    def snapshot_page_paths(page_info):
        paths=original_page_paths(page_info)
        paths['screenshot']='F:\\code\\resumeagent\\resumeagent-main\\test-artifacts\\contract-site\\index.png'
        return paths
    agent.page_paths=snapshot_page_paths
    agent.task = dict(profile,img='reference.png')
    agent.tools.call = lambda *a,**kw:SimpleNamespace(value={'html':'<html></html>','css':'body{}'})
    messages = {}
    for language,framework,vision,image in itertools.product(('en','zh'),('Tailwind',None),(False,True,None,0),(None,'reference.png')):
        agent.language,agent.css_frame,agent.vision = language,framework,vision
        agent.task['img'] = image
        agent.user_feedback = 'Make the header blue'
        key = repr((language,framework,vision,image))
        messages['generation'+key] = digest(Generator.get_write_original_website_messages(agent,page))
        messages['refinement'+key] = digest(Refiner.get_refine_messages(agent,page))

    wire = {}
    cases = [
        [{'role':'user','content':[{'type':'text','text':'Example'}]}],
        [{'role':'user','content':[{'type':'image','url':'https://example.invalid/reference.png'},{'type':'text','text':'Example'}]}],
        [{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,AA=='}}]}],
        [{'role':'tool','content':{'result':'example'}}],
        [{'role':'user','content':'Example'}],
    ]
    openai = openai_llm.__new__(openai_llm)
    qwen = qwen_llm.__new__(qwen_llm)
    api = MagicMock()
    api.with_options.return_value = api
    api.multimodal.chat.create.return_value = SimpleNamespace(usage=None,output=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='answer'))]))
    qwen.client = api
    for i, value in enumerate(cases):
        for options in ({},{'model':'example-model','temperature':.1,'top_p':.5,'max_tokens':123,'timeout':9,'preserve_thinking':True}):
            key = repr((i,options))
            wire['openai'+key] = digest(openai._params(value,options))
            api.reset_mock()
            try:
                # Freeze the historical explicit model; the user changed the default
                # to Flash, which is checked separately in the adapter regressions.
                answer = qwen.response(value,_max_attempts=1,**({'model':'qwen3.8-max'} | options))
                wire['qwen'+key] = digest({'request':api.multimodal.chat.create.call_args.kwargs,'answer':answer})
            except Exception as exc:
                wire['qwen'+key] = {'error':type(exc).__name__}

    with tempfile.TemporaryDirectory() as directory:
        db = Database(Path(directory)/'schema.sqlite3')
        with db.connect() as connection:
            schema = [dict(row) for row in connection.execute("SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name")]

    prompt_files = {}
    for path in (ROOT/'resumeagent/prompts').glob('*.py'):
        if path.name != '__init__.py':
            prompt_files[path.name] = ast.dump(ast.parse(path.read_text(encoding='utf-8-sig')))
    return {'prompts':prompts,'agent_messages':messages,'llm_requests':wire,
            'prompt_ast':digest(prompt_files),'database_schema':schema,
            'mcp_schemas':{name:model.model_json_schema() for name,model in SCHEMAS.items()},
            'agent_signature':str(inspect.signature(HomepageDesignAgent))}


class RefactorContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        cls.design = json.loads(PROMPT_SNAPSHOT.read_text(encoding='utf-8'))
        cls.actual = capture_contracts()

    def test_prompt_content_matches_explicit_planner_protocol_v3_baseline(self):
        self.assertEqual(self.design['version'], 'planner-protocol-v3')
        self.assertEqual(self.actual['prompt_ast'],self.design['prompt_ast'])
        self.assertEqual(self.actual['prompts'],self.design['prompts'])

    def test_agent_messages_and_constructor_are_unchanged(self):
        self.assertEqual(self.actual['agent_messages'],self.design['agent_messages'])
        self.assertEqual(self.actual['agent_signature'],self.expected['agent_signature'])

    def test_provider_request_parameters_are_unchanged(self):
        self.assertEqual(self.actual['llm_requests'],self.expected['llm_requests'])

    def test_mcp_schemas_and_database_schema_are_unchanged(self):
        self.assertEqual(self.actual['mcp_schemas'],self.expected['mcp_schemas'])
        self.assertEqual(self.actual['database_schema'],self.expected['database_schema'])


if __name__ == '__main__':
    if '--record' in sys.argv:
        if SNAPSHOT.exists():
            raise SystemExit('Refusing to overwrite the recorded pre-refactor contracts')
        SNAPSHOT.write_text(json.dumps(capture_contracts(),ensure_ascii=False,indent=2),encoding='utf-8')
        print('Recorded pre-refactor Prompt, request, schema and message contracts')
    else:
        unittest.main()
