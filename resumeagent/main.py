"""Public agent facade, session state and concurrent workflow orchestration."""
import logging
import asyncio
import os
from resumeagent.utils import wrap_func

from resumeagent.agents.base import BaseAgent
from resumeagent.agents.planner import Planner
from resumeagent.agents.generator import Generator
from resumeagent.agents.refiner import Refiner
from resumeagent.tools.filesystem import Filesystem
from resumeagent.tools.browser import Webserver
from resumeagent.llm.client import read_tokens

logger = logging.getLogger(__name__)


class HomepageDesignAgent(Planner, Generator, Refiner, Filesystem, BaseAgent):
    def __init__(self, model="gpt4o-0513",save_file = "saves/",**kwargs) -> None:
        super().__init__(model, llm=kwargs.get("llm"))
        self.task = {"img":None,"basic_information":None, "academic_achievements":None, "experience":None, "professional_skills":None}
        self.task_queue = []
        self.memory = []
        tokens = read_tokens()
        self.begin_prompt_tokens = tokens.get(self.model, [0, 0])[0]
        self.begin_completion_tokens = tokens.get(self.model, [0, 0])[1]
        self.max_cost_prompt_tokens = 1000000
        self.max_cost_completion_tokens = 1000000
        self.webserver = None
        self.webserver = kwargs.get("browser") or Webserver(save_file)
        self.user_feedback = None
        if not os.path.exists(save_file):
            os.makedirs(save_file)

        self.css_frame = "Tailwind"
        self.status = "student"
        self.industry = "tech"
        self.gen_img = "Gen"
        self.local_img_storage = []
        self.local_img_storage_path = None
        self.local_img_storage_copy = []
        self.local_img_storage_en = []
        self.local_img_storage_zh = []
        self.language = "en"
        self.save_file = save_file
        self.total_prompt_cost_tokens = 0
        self.total_completion_cost_tokens = 0
        self.refine_times = 2
        self.vision = True
        self.image_client = kwargs.get('image_client')
        from harness.tools import build_tools
        self.tools = build_tools(self)
        self.runtime_options = kwargs.get('runtime_options', {})
        self.last_run_id = None
        self.active_runtime = None


    def act(self,**kwargs):
        self.publish_task(**kwargs)
        self.deal_task()
        return "done"


    def _runtime(self):
        from harness.runtime import Runtime
        from harness.budget import BudgetLimits
        options = dict(self.runtime_options)
        from dataclasses import replace
        limits = options.pop('limits', None)
        if limits is None:
            limits = BudgetLimits(max_iterations=self.refine_times,
                                  max_prompt_tokens=self.max_cost_prompt_tokens,
                                  max_completion_tokens=self.max_cost_completion_tokens)
        else:
            limits = replace(limits,max_iterations=self.refine_times)
        return Runtime(self, limits=limits, **options)

    def deal_task(self):
        runtime = self._runtime()
        run_id = runtime.create_run(output_dir=self.save_file)
        result = asyncio.run(runtime.execute(run_id))
        self.last_run_id = run_id
        if result['status'] != 'completed':
            from harness.runtime import RunStopped
            raise RunStopped(result, runtime.tracer.diagnostic_path(run_id))
        return result

    async def deal_task_async(self, pages):
        runtime = self._runtime()
        run_id = runtime.create_run(pages=pages, output_dir=self.save_file)
        result = await runtime.execute(run_id)
        if result['status'] != 'completed':
            from harness.runtime import RunStopped
            raise RunStopped(result, runtime.tracer.diagnostic_path(run_id))
        return result

    def cancel_run(self):
        if self.active_runtime is not None:
            self.active_runtime.cancel(self.last_run_id)

    def managed_action(self, method, *args, **kwargs):
        runtime = self._runtime()
        run_id = runtime.create_run(output_dir=self.save_file,action={'method':method,'args':list(args),'kwargs':kwargs})
        result = asyncio.run(runtime.execute(run_id))
        if result['status'] != 'completed':
            from harness.runtime import RunStopped
            raise RunStopped(result, runtime.tracer.diagnostic_path(run_id))
        tasks = runtime.state.tasks(run_id)
        return tasks[-1]['result'].get('value')

    def change_save_file(self,save_file):
        save_file = save_file or "saves/"
        self.save_file = save_file
        self.webserver.save_file = save_file
        logger.info(f"Attempting to create directory: {save_file}")
        if not os.path.exists(save_file):
            os.makedirs(save_file)


    def chat(self, query, **kwargs):
        self.memory.append({"role":"user","content":query})
        if len(self.memory) > 10:
            self.memory = self.memory[-10:]
        response = wrap_func(self.get_answer, messages=self.memory, **kwargs)
        if not response:
            logger.warning("Failed to get the response.")
            return
        self.memory.append({"role":"assistant","content":response})
        return response


    def publish_task(self,img = None, basic_information = None, academic_achievements = None, experience=None, professional_skills=None,feedback=None,refine_times= None, max_cost_prompt_tokens = 1000000,max_cost_completion_tokens = 1000000):
        self.task = {"img":img,"basic_information":basic_information, "academic_achievements":academic_achievements, "experience":experience, "professional_skills":professional_skills, "feedback":feedback}
        self.user_feedback = feedback
        self.max_cost_prompt_tokens = max_cost_prompt_tokens
        self.max_cost_completion_tokens = max_cost_completion_tokens
        self.refine_times = refine_times if refine_times is not None else 2


    def check_cost(self):
        tokens = read_tokens()
        current_prompt_tokens = tokens.get(self.model, [0, 0])[0]
        current_completion_tokens = tokens.get(self.model, [0, 0])[1]
        self.total_prompt_cost_tokens = current_prompt_tokens - self.begin_prompt_tokens
        self.total_completion_cost_tokens = current_completion_tokens - self.begin_completion_tokens
        if self.total_prompt_cost_tokens > self.max_cost_prompt_tokens or self.total_completion_cost_tokens > self.max_cost_completion_tokens:
            return False
        return True


    async def generate_and_refine_single_page_async(self, page_info):
        return await self.deal_task_async([page_info])

    def close(self):
        self.webserver.stop()


def main(argv=None):
    import argparse
    import json
    from dataclasses import replace
    from harness.runtime import Runtime
    from harness.budget import BudgetLimits
    from resumeagent.config import default_model
    parser = argparse.ArgumentParser(description='ResumeAgent Harness Runtime')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--model', default=default_model())
    parser.add_argument('--save_file', default=None)
    for name in ['basic_information','academic_achievements','experience','professional_skills','img','feedback']:
        parser.add_argument('--'+name, default=None)
    parser.add_argument('--refine_times','--max_iterations', dest='refine_times', type=int, default=None)
    parser.add_argument('--storage_root', default=None)
    parser.add_argument('--database', dest='database_path', default=None)
    controls = parser.add_mutually_exclusive_group()
    for name in ('resume','trace','status','cancel'):
        controls.add_argument('--'+name, metavar='RUN_ID')
    for name,kind in [('max_cost',float),('max_prompt_tokens',int),('max_completion_tokens',int),('max_concurrency',int),('request_timeout',float),('max_run_seconds',float),('max_retries',int)]:
        parser.add_argument('--'+name, type=kind, default=None)
    args = parser.parse_args(argv)
    options = {'storage_root':args.storage_root, 'database_path':args.database_path}
    overrides = {name:getattr(args,name) for name in ('max_cost','max_prompt_tokens','max_completion_tokens','max_concurrency','request_timeout','max_run_seconds','max_retries') if getattr(args,name) is not None}
    if args.refine_times is not None:
        overrides['max_iterations'] = args.refine_times
    if args.trace or args.status or args.cancel:
        runtime = Runtime(**options)
        run_id = args.trace or args.status or args.cancel
        if args.trace:
            for event in runtime.tracer.query(run_id):
                print(json.dumps(event,ensure_ascii=False))
        elif args.cancel:
            runtime.cancel(run_id)
            print(json.dumps({'id':run_id,'cancel_requested':True}))
        else:
            run = runtime.state.get_run(run_id)
            summary = {k:run[k] for k in ('id','status','stage','created_at','updated_at','retries','files','error','usage','elapsed')}
            summary['pages'] = [{k:p[k] for k in ('id','status','stage','iteration','retries','files','error')} for p in runtime.state.pages(run_id)]
            print(json.dumps(summary,ensure_ascii=False,indent=2))
        return
    limits = replace(BudgetLimits(),**overrides)
    agent = HomepageDesignAgent(model=args.model,save_file=args.save_file or 'saves/',runtime_options={**options,'limits':limits})
    try:
        if args.gui:
            from resumeagent.frontend.gui import Application
            Application(agent=agent).mainloop()
            return
        runtime = Runtime(agent,limits=limits,**options)
        if args.resume:
            if overrides:
                previous = BudgetLimits(**runtime.state.get_run(args.resume)['limits'])
                runtime.set_limits(args.resume,replace(previous,**overrides))
            result = asyncio.run(runtime.resume(args.resume))
        else:
            profile = {name:getattr(args,name) for name in ('basic_information','academic_achievements','experience','professional_skills','img')}
            run_id = runtime.create_run(profile,feedback=args.feedback,output_dir=args.save_file)
            print('Run ID:',run_id,flush=True)
            result = asyncio.run(runtime.execute(run_id))
        print(json.dumps({key:result[key] for key in ('id','status','stage','usage','files','error')},ensure_ascii=False,indent=2))
        if result['status'] != 'completed':
            raise SystemExit(1)
    finally:
        agent.close()


if __name__ == '__main__':
    main()
