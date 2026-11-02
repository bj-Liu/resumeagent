"""Single workflow owner; business reasoning stays in Planner/Generator/Refiner."""
import asyncio
from copy import copy
from pathlib import Path
import time
from uuid import uuid4
from storage.database import Database
from .budget import Budget, BudgetExceeded, BudgetLimits, RequestTimedOut, RunCancelled
from .context import Context, CURRENT_EXECUTION, ExecutionScope
from .state import StateStore
from .tools import build_tools
from .tracing import Tracer, safe_error


class RunStopped(RuntimeError):
    def __init__(self, result, diagnostic_path=None):
        self.result = result
        message = f"Run {result['id']}: {result['status']} ({result.get('error') or 'see trace'})"
        if diagnostic_path and Path(diagnostic_path).is_file():
            message += f'\nDeveloper diagnostics: {diagnostic_path}'
        super().__init__(message)


class _Response:
    """Keep asyncio debug Task representations from exposing model output."""
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return '<LLM response redacted>'


class Runtime:
    ACTIONS = {'plan':'planning', 'write_original_website':'generation', 'refine':'refinement',
               'refine_page':'specification', 'complete_page':'specification',
               'load_local_img_storage':'catalog'}
    def __init__(self, agent=None, *, database_path=None, storage_root=None, limits=None):
        self.agent = agent
        self.root = Path(storage_root or Path(__file__).resolve().parents[1] / 'storage').resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root/'outputs').mkdir(exist_ok=True)
        (self.root/'runs').mkdir(exist_ok=True)
        self.state = StateStore(Database(database_path or self.root/'resumeagent.sqlite3'))
        self.tracer = Tracer(self.state.db, self.root/'runs')
        self.limits = limits or BudgetLimits()
        self.budget = None
        self._pending = set()
        self._executing = False
        self._owner = uuid4().hex
        self.run_id = None

    def create_run(self, profile=None, *, pages=None, feedback=None, output_dir=None, action=None, origin=None, language=None):
        if self.agent is None:
            raise ValueError('Creating a run requires an agent')
        agent = self.agent
        profile = dict(profile if profile is not None else agent.task)
        # Only user task fields/settings are persisted, never backend configuration or API keys.
        profile = {key:profile.get(key) for key in ('basic_information','academic_achievements','experience','professional_skills','img')}
        settings = {key:getattr(agent,key) for key in ('model','css_frame','vision','gen_img','language','status','industry','local_img_storage','local_img_storage_path','local_img_storage_en','local_img_storage_zh')}
        settings['execution_mode'] = getattr(agent,'execution_mode','live')
        settings['rendering_mode'] = getattr(agent,'rendering_mode','selenium')
        if language is not None:
            if language not in ('en','zh'):
                raise ValueError('Invalid language')
            settings['language'] = language
        if origin is not None:
            settings['origin'] = origin
        if action:
            if action.get('method') not in self.ACTIONS:
                raise ValueError('Unsupported managed action')
            settings['action'] = action
        context = Context(profile, agent.user_feedback if feedback is None else feedback, pages, settings)
        run_id = self.state.create_run(context.to_dict(), self.limits.to_dict(), {})
        directory = Path(output_dir).resolve() if output_dir else self.root/'outputs'/run_id
        directory.mkdir(parents=True, exist_ok=True)
        self.state.update_run(run_id, files={'output_dir':str(directory)})
        self.tracer.emit(run_id, 'run.created', status='created', stage='creation')
        agent.last_run_id = run_id
        return run_id

    @classmethod
    def configured(cls, *, storage_root=None, limits=None, model=None, browser=None):
        """Build a configured business session behind the Runtime boundary."""
        from resumeagent.main import HomepageDesignAgent
        from resumeagent.config import default_model
        from resumeagent.tools.browser import Webserver
        selected = model or default_model()
        root = Path(storage_root or Path(__file__).resolve().parents[1]/'storage').resolve()
        agent = HomepageDesignAgent(model=selected,save_file=str(root/'outputs'),
                                    browser=Webserver(str(root/'outputs'),web_type=browser) if browser else None)
        agent.gen_img = False
        return cls(agent,storage_root=root,limits=limits)

    def generation_status(self, run_id, *, origin=None):
        record = self.state.get_run(run_id)
        if origin is not None and record['context']['settings'].get('origin') != origin:
            raise PermissionError('Run is not available to this interface')
        pages = self.state.pages(run_id)
        total = len(pages) or len(record['context'].get('plan') or [])
        completed = sum(page['status']=='completed' for page in pages)
        tasks = self.state.tasks(run_id)
        return {'run_id':run_id,'status':record['status'],'stage':record['stage'],
                'execution_mode':record['context']['settings'].get('execution_mode','unknown'),
                'rendering_mode':record['context']['settings'].get('rendering_mode','unknown'),
                'model':record['context']['settings']['model'],
                'progress':{'pages_total':total,'pages_completed':completed,
                            'fraction':completed/total if total else None,
                            'tasks_total':len(tasks),'tasks_completed':sum(t['status']=='completed' for t in tasks)},
                'pages':[{'page_id':p['id'],'html_name':p['spec'].get('html_name'),
                          'status':p['status'],'stage':p['stage'],'iteration':p['iteration'],
                          'retries':p['retries'],'error':p['error']} for p in pages],
                'usage':{**record['usage'],'token_source':'synthetic_fixture_usage' if record['context']['settings'].get('execution_mode')=='mock' else 'provider_reported_if_available'},'error':record['error'],
                'cancel_requested':bool(record['cancel_requested']),
                'created_at':record['created_at'],'updated_at':record['updated_at']}

    def preview_page(self, run_id, page_id, *, origin=None):
        from .tools import ToolRegistry, Parameter
        from resumeagent.tools.filesystem_helpers import preview_metadata
        self.generation_status(run_id,origin=origin)
        page = self.state.page(page_id)
        if page['run_id'] != run_id:
            raise PermissionError('Page does not belong to this run')
        record = self.state.get_run(run_id)
        output = Path(record['files']['output_dir']).resolve()
        # External interfaces cannot turn stored artifact metadata into an arbitrary file reader.
        if origin is not None and (not output.is_relative_to(self.root) or output != (self.root/'outputs'/run_id).resolve()):
            raise PermissionError('Run output is outside the interface output directory')
        registry = ToolRegistry()
        registry.register('filesystem.preview_metadata','Read confined preview metadata',
                          {'root':Parameter(str),'files':Parameter(dict)},preview_metadata)
        self.tracer.emit(run_id,'preview.started',tool='filesystem.preview_metadata',stage='preview',page_id=page_id,agent='Tools')
        try:
            metadata = registry.call('filesystem.preview_metadata',root=str(output),files=page['files']).value
        except Exception as exc:
            self.tracer.emit(run_id,'preview.failed',tool='filesystem.preview_metadata',error=safe_error(exc),page_id=page_id,stage='preview')
            raise
        self.tracer.emit(run_id,'preview.completed',tool='filesystem.preview_metadata',page_id=page_id,stage='preview')
        return {'run_id':run_id,'page_id':page_id,'status':page['status'],'stage':page['stage'],
                'iteration':page['iteration'],'is_final':page['status']=='completed',
                'rendering_mode':record['context']['settings'].get('rendering_mode','unknown'),**metadata}

    async def aclose(self):
        """Drain managed background work before releasing browser resources."""
        while self._pending:
            await asyncio.gather(*tuple(self._pending),return_exceptions=True)
        if self.agent is not None:
            await asyncio.to_thread(self.agent.close)

    def cancel(self, run_id):
        self.state.get_run(run_id)
        self.state.update_run(run_id, cancel_requested=1)
        self.tracer.emit(run_id, 'run.cancel_requested', status='cancelling')

    def set_limits(self, run_id, limits):
        record = self.state.get_run(run_id)
        if record['lease_owner'] and record['lease_until'] > time.time():
            raise RuntimeError('Cannot change limits while a run is executing')
        self.state.update_run(run_id, limits=limits.to_dict())

    def _session(self, stage, page=None):
        session = copy(self.agent)
        session.task = {key:self.context.profile.get(key) for key in ('basic_information','academic_achievements','experience','professional_skills','img')}
        session.memory = []
        session.task_queue = self.context.plan or []
        session.stage_context = self.context.build(stage, page)
        for key, value in self.context.settings.items():
            setattr(session, key, value)
        session.save_file = self.output_dir
        session.user_feedback = self.context.feedback
        if stage == 'refinement' and page:
            visual = page['checkpoint'].get('last_result', {}).get('feedback', '')
            if visual:
                session.user_feedback = '\n'.join(filter(None, [self.context.feedback, visual]))
        session.max_agent_attempts = 1
        session.tools = build_tools(session)
        return session

    def track_tool(self, task, name):
        scope = CURRENT_EXECUTION.get()
        self._pending.add(task)
        self.budget.pending_tools += 1
        def finished(worker):
            self._pending.discard(worker)
            self.budget.pending_tools -= 1
            error = None if worker.cancelled() else worker.exception()
            self.tracer.emit(scope.run_id,'tool.worker_finished',tool=name,status='failed' if error else 'completed',error=safe_error(error) if error else None)
            self.state.update_run(scope.run_id,usage=self.budget.usage())
            if not self._executing and not self._pending:
                self.state.release(scope.run_id,self._owner)
        task.add_done_callback(finished)

    async def llm_call(self, agent, messages, kwargs):
        """One managed request. SDK retries are disabled; stage retries own recovery."""
        from resumeagent.llm.client import usage_observer
        budget = self.budget
        budget.check()
        await budget.slots.acquire()
        try:
            budget.check()
        except BaseException:
            budget.slots.release()
            raise
        request_id = uuid4().hex
        model = kwargs.get('model', agent.model)
        scope = CURRENT_EXECUTION.get()
        request_timeout = min(kwargs.get('timeout', budget.limits.request_timeout),
                              budget.limits.request_timeout)

        kwargs = dict(
            kwargs,
            timeout=request_timeout,
            _max_attempts=1
        )

        observed = False
        started = time.monotonic()

        def record(model, prompt, completion):
            nonlocal observed
            observed = True
            budget.record(request_id, model, prompt, completion)

        async def invoke():
            token = usage_observer.set(record)
            try:
                if hasattr(agent.llm, 'response_async'):
                    return _Response(await agent.llm.response_async(messages, **kwargs))
                return _Response(await asyncio.to_thread(agent.llm.response, messages, **kwargs))
            finally:
                usage_observer.reset(token)

        self.tracer.emit(self.run_id, 'llm.started', request_id=request_id, model=model,
                         message_count=len(messages), image_count=sum(1 for m in messages if isinstance(m.get('content'),list) for b in m['content'] if b.get('type') in ('image','image_url')))
        request = asyncio.create_task(invoke())
        self._pending.add(request)
        budget.pending_requests += 1

        def finished(task):
            self._pending.discard(task)
            budget.pending_requests -= 1
            budget.slots.release()
            # Consume abandoned request exceptions and retain late usage attribution.
            if not task.cancelled():
                task.exception()
            self.state.update_run(scope.run_id, usage=budget.usage())
            if not self._executing and not self._pending:
                self.state.release(scope.run_id, self._owner)

        request.add_done_callback(finished)
        try:
            response = await asyncio.wait_for(asyncio.shield(request), kwargs['timeout'])
            if not observed:
                self.tracer.emit(self.run_id, 'llm.usage_unavailable', request_id=request_id, model=model)
                if any(v is not None for v in (budget.limits.max_cost, budget.limits.max_prompt_tokens, budget.limits.max_completion_tokens)):
                    raise BudgetExceeded('usage_unavailable')
            self.tracer.emit(self.run_id, 'llm.completed', request_id=request_id, model=model, status='completed', duration_ms=(time.monotonic()-started)*1000)
            budget.check()
            return response.text
        except asyncio.TimeoutError:
            budget.stopped = RequestTimedOut('request_timeout')
            self.tracer.emit(self.run_id, 'llm.failed', request_id=request_id, model=model, error='RequestTimedOut', duration_ms=(time.monotonic()-started)*1000)
            raise budget.stopped from None
        except asyncio.CancelledError:
            self.tracer.emit(self.run_id, 'llm.cancelled', request_id=request_id, model=model, status='cancelled', duration_ms=(time.monotonic()-started)*1000)
            raise
        except Exception as exc:
            self.tracer.exception(self.run_id, exc, request_id=request_id, model=model)
            self.tracer.emit(self.run_id, 'llm.failed', request_id=request_id, model=model, error=safe_error(exc), duration_ms=(time.monotonic()-started)*1000)
            raise

    async def _perform(self, stage, operation, page=None, iteration=0, advance=None, use_cached=False):
        page_id = page['id'] if page else ''
        task = self.state.task(self.run_id, stage, page_id, iteration)
        if use_cached and task['status'] == 'completed':
            return task['result']
        agent_name = {'planning':'Planner','generation':'Generator','refinement':'Refiner','evaluation':'Refiner'}.get(stage,'Tools')
        token = CURRENT_EXECUTION.set(ExecutionScope(self,self.run_id,task['id'],page_id,stage,agent_name))
        try:
            for retry in range(self.budget.limits.max_retries+1):
                self.budget.check()
                self.state.begin_task(task['id'])
                self.state.update_run(self.run_id, stage=stage)
                started = time.monotonic()
                self.tracer.emit(self.run_id, 'task.started', status='running', retry=retry, iteration=iteration)
                try:
                    result = await operation(self._session(stage,page))
                    self.budget.check()
                    continuation = advance(result) if advance else {}
                    self.state.complete_task(task['id'], result, **continuation)
                    self.tracer.emit(self.run_id, 'task.completed', status='completed', retry=retry, iteration=iteration, duration_ms=(time.monotonic()-started)*1000)
                    return result
                except asyncio.CancelledError:
                    self.state.fail_task(task['id'], 'interrupted', 'CancelledError')
                    self.tracer.emit(self.run_id, 'task.interrupted', status='interrupted', duration_ms=(time.monotonic()-started)*1000)
                    raise
                except (BudgetExceeded, RunCancelled, RequestTimedOut):
                    self.state.fail_task(task['id'], 'interrupted', 'ExecutionStopped')
                    raise
                except Exception as exc:
                    self.tracer.exception(self.run_id, exc, retry=retry)
                    will_retry = retry < self.budget.limits.max_retries
                    self.state.fail_task(task['id'], 'retrying' if will_retry else 'failed', safe_error(exc), retry=will_retry)
                    self.tracer.emit(self.run_id, 'task.failed', status='retrying' if will_retry else 'failed', retry=retry,error=safe_error(exc),duration_ms=(time.monotonic()-started)*1000)
                    if not will_retry:
                        raise
                    await asyncio.sleep(min(.1 * 2**retry, 2))
        finally:
            CURRENT_EXECUTION.reset(token)

    async def _page(self, page):
        page_id = page['id']
        # Checksums apply to the final page only; earlier stages share the current HTML path.
        session = self._session('recovery',page)
        scope_token = CURRENT_EXECUTION.set(ExecutionScope(self,self.run_id,'',page_id,'recovery','Tools'))
        try:
            if page['status'] == 'completed':
                valid = (await session.tools.acall('filesystem.check_artifacts', files=page['files'], fingerprints=page['checkpoint'].get('last_result',{}).get('fingerprints'))).value
                if valid:
                    self.tracer.emit(self.run_id, 'page.skipped', status='completed',reason='checkpoint_verified')
                    return
                self.state.reset_page(page_id)
            elif page['stage'] != 'generation':
                source_files = {k:v for k,v in page['files'].items() if k in ('html','css')}
                if not (await session.tools.acall('filesystem.check_artifacts',files=source_files)).value:
                    self.state.reset_page(page_id)
        finally:
            CURRENT_EXECUTION.reset(scope_token)
        self.state.mark_page(page_id, 'running')
        try:
            while True:
                self.budget.check()
                page = self.state.page(page_id)
                stage, iteration = page['stage'], page['iteration']
                if stage == 'completion':
                    self.tracer.emit(self.run_id, 'page.completed', page_id=page_id,stage='completion',status='completed',iteration=iteration)
                    return

                def advance(result, next_stage, next_iteration=iteration):
                    return dict(page_id=page_id,next_stage=next_stage,iteration=next_iteration,files=result.get('files',{}))

                if stage in ('generation', 'refinement'):
                    async def produce(agent):
                        operation = agent.generate_code_async if stage == 'generation' else agent.refine_code_async
                        code = await operation(page['spec'])
                        saved = await agent.tools.acall('filesystem.save_page', page_info=page['spec'], **code)
                        return {'files': saved.value}
                    await self._perform(stage, produce, page, iteration, lambda r: advance(r, 'rendering'))
                elif stage == 'rendering':
                    async def render(agent):
                        paths = agent.page_paths(page['spec'])
                        result = await agent.tools.acall('browser.render', html_path=paths['html'], screenshot_path=paths['screenshot'])
                        return {'files':result.value}
                    await self._perform(stage,render,page,iteration,lambda r:advance(r,'evaluation'))
                elif stage == 'evaluation':
                    async def evaluate(agent):
                        if not agent.vision:
                            self.tracer.emit(self.run_id,'evaluation.skipped',reason='vision_disabled')
                            return {'needs_refinement':True,'feedback':''}
                        return await agent.evaluate_screenshot_async(page['spec'],page['files']['screenshot'])
                    def evaluated(result):
                        refine = result['needs_refinement'] and iteration < self.budget.limits.max_iterations
                        if result['needs_refinement'] and not refine:
                            self.tracer.emit(self.run_id,'iteration.limit',reason='max_iterations',iteration=iteration)
                        return advance(result,'refinement' if refine else 'validation', iteration+1 if refine else iteration)
                    await self._perform(stage,evaluate,page,iteration,evaluated)
                elif stage == 'validation':
                    async def validate(agent):
                        return (await agent.tools.acall('filesystem.validate_page', page_info=page['spec'])).value
                    await self._perform(stage,validate,page,iteration,lambda r:advance(r,'completion'))
                else:
                    raise ValueError('Unknown checkpoint stage')
        except asyncio.CancelledError:
            self.state.mark_page(page_id,'interrupted','CancelledError')
            raise
        except (BudgetExceeded, RunCancelled, RequestTimedOut):
            self.state.mark_page(page_id,'interrupted','ExecutionStopped')
            raise
        except Exception as exc:
            self.state.mark_page(page_id,'failed',safe_error(exc))
            raise

    async def _workflow(self):
        if self.context.settings.get('action'):
            await self._action_workflow()
            return
        if self.context.plan is None:
            async def plan(agent):
                return {'pages':await agent.plan_async()}
            result = await self._perform('planning',plan,use_cached=True)
            self.context.plan = result['pages']
            self.state.update_run(self.run_id,context=self.context.to_dict())
        else:
            async def accept_plan(agent):
                await agent.tools.acall('filesystem.validate_plan',pages=self.context.plan)
                await agent.tools.acall('filesystem.write_json',path=str(Path(self.output_dir)/'pages.json'),data=self.context.plan)
                return {'pages':self.context.plan}
            await self._perform('planning',accept_plan,use_cached=True)
        self.agent.task_queue = self.context.plan
        pages = self.state.create_pages(self.run_id,self.context.plan)
        workers = [asyncio.create_task(self._page(page)) for page in pages]
        try:
            results = await asyncio.gather(*workers,return_exceptions=True)
            stop = next((r for r in results if isinstance(r,(BudgetExceeded,RunCancelled,RequestTimedOut))),None)
            if stop:
                raise stop
            if any(isinstance(r,BaseException) for r in results):
                raise RuntimeError('One or more pages failed; see page checkpoints')
        finally:
            for worker in workers:
                if not worker.done():
                    worker.cancel()
            await asyncio.gather(*workers,return_exceptions=True)
        async def validate_site(agent):
            # All target pages must exist after every page worker has completed.
            for page in self.context.plan:
                if not (await agent.tools.acall('filesystem.exists',path=str(Path(self.output_dir)/page['html_name']))).value:
                    raise ValueError('Missing website page')
            return {'valid':True,'page_count':len(self.context.plan)}
        await self._perform('validation',validate_site)

    async def _action_workflow(self):
        """Interactive GUI actions use the same task, budget, tool and trace boundary."""
        action = self.context.settings['action']
        method = action['method']
        args = action.get('args', [])
        page = None
        if method in ('write_original_website', 'refine'):
            page = self.state.create_pages(self.run_id, [args[0]])[0]
            self.state.mark_page(page['id'], 'running')
        async def invoke(agent):
            value = await asyncio.to_thread(getattr(agent,method), *args, **action.get('kwargs',{}))
            if method in ('refine_page','complete_page') and value is None:
                raise ValueError('Agent action returned no result')
            result = {'value':value}
            if page:
                validation = (await agent.tools.acall('filesystem.validate_page',page_info=args[0])).value
                result.update(files=validation['files'],fingerprints=validation['fingerprints'])
            for key in ('task_queue','local_img_storage','local_img_storage_en','local_img_storage_zh'):
                setattr(self.agent,key,getattr(agent,key))
            return result
        def advance(result):
            return {'page_id':page['id'],'next_stage':'completion','iteration':0,'files':result['files']}
        result = await self._perform(self.ACTIONS[method],invoke,page=page,advance=advance if page else None)
        if method == 'plan':
            self.context.plan = result['value']
            self.state.update_run(self.run_id,context=self.context.to_dict())
            self.state.create_pages(self.run_id,result['value'])

    async def _watch(self):
        last_heartbeat = 0
        while True:
            self.budget.check()
            if time.monotonic()-last_heartbeat > 2:
                self.state.heartbeat(self.run_id,self._owner)
                self.budget.snapshot()
                last_heartbeat = time.monotonic()
            await asyncio.sleep(.05)

    async def execute(self, run_id, *, clear_cancel=False):
        if self._executing or self._pending:
            raise RuntimeError('Runtime is busy or draining an in-flight request')
        if self.agent is None:
            raise ValueError('Execution requires an agent')
        record = self.state.get_run(run_id)
        self.state.claim(run_id,self._owner)
        self.run_id = run_id
        self.loop = asyncio.get_running_loop()
        self._executing = True
        self.agent.active_runtime = self
        self.agent.last_run_id = run_id
        self.output_dir = record['files']['output_dir']
        self.context = Context.from_dict(record['context'])
        self.budget = Budget(self.state,self.tracer,run_id,BudgetLimits(**record['limits']))
        self.state.update_run(run_id,status='running',error=None,**({'cancel_requested':0} if clear_cancel else {}))
        self.tracer.emit(run_id,'run.started',status='running',reason='resume' if record['status'] != 'created' else 'new')
        workflow = asyncio.create_task(self._workflow())
        watcher = asyncio.create_task(self._watch())
        status, error = 'completed', None
        try:
            done,_ = await asyncio.wait([workflow,watcher],return_when=asyncio.FIRST_COMPLETED)
            if watcher in done:
                await watcher
            await workflow
        except asyncio.CancelledError:
            status,error = 'cancelled','CancelledError'
        except RunCancelled:
            status,error = 'cancelled','RunCancelled'
        except BudgetExceeded as exc:
            status,error = 'budget_exceeded', str(exc)
        except RequestTimedOut:
            status,error = 'timed_out','request_timeout'
        except Exception as exc:
            self.tracer.exception(run_id, exc, stage=self.state.get_run(run_id)['stage'])
            status,error = 'failed',safe_error(exc)
        finally:
            # Prevent a late sync SDK result from admitting any follow-up writes/calls.
            if status != 'completed' and self.budget.stopped is None:
                self.budget.stopped = RunCancelled('Execution stopped')
            workflow.cancel(); watcher.cancel()
            await asyncio.gather(workflow,watcher,return_exceptions=True)
            self.state.interrupt_active(run_id,'interrupted',error)
            self.budget.snapshot()
            self.state.update_run(run_id,status=status,stage='completion' if status == 'completed' else self.state.get_run(run_id)['stage'],error=error)
            self.tracer.emit(run_id,'run.finished',status=status,error=error,pending_requests=self.budget.pending_requests)
            self._executing = False
            if not self._pending:
                self.state.release(run_id,self._owner)
            else:
                self.state.heartbeat(run_id,self._owner,self.budget.limits.request_timeout+30)
            self.agent.active_runtime = None
        return self.state.get_run(run_id)

    async def resume(self, run_id):
        return await self.execute(run_id,clear_cancel=True)
