"""GUI-only tool actions using the existing Runtime execution/checkpoint machinery.

Business agents still use their public managed_action/deal_task APIs. This small
extension supplies the missing tool-only entry point; no core module is changed.
"""
import asyncio
from copy import deepcopy
from pathlib import Path
import shutil
from urllib.parse import urlsplit
import tempfile

from harness.runtime import Runtime, RunStopped
from harness.tools import Parameter, ToolValidationError


class GuiToolRuntime(Runtime):
    ACTIONS = {**Runtime.ACTIONS, 'gui_tool': 'tools'}

    async def _action_workflow(self):
        action = self.context.settings['action']
        if action['method'] != 'gui_tool':
            return await super()._action_workflow()

        async def invoke(agent):
            register_gui_tools(agent)
            value = await agent.tools.acall(action['kwargs']['tool'], **action['kwargs']['parameters'])
            return {'value': value.value}
        await self._perform('tools', invoke)


def register_gui_tools(agent):
    root = Path(agent.save_file).resolve()

    def confined(path):
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(root):
            raise ToolValidationError('GUI artifact path escapes the output directory')
        return resolved

    def reference(url, screenshot_path):
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ToolValidationError('Reference website must be an HTTP(S) URL without credentials')
        target = confined(screenshot_path)
        agent.webserver.get_screenshot(url, str(target), False)
        return str(target)

    def backup(page_info, restore=False):
        paths = agent.page_paths(page_info)
        selected = {key: confined(value) for key, value in paths.items() if value and key in ('html','css','screenshot')}
        backups = {key: confined(root/'backup'/path.relative_to(root).parent/('backup_'+path.name))
                   for key,path in selected.items()}
        if restore:
            # Validate the entire set before overwriting any current file.
            for key in selected:
                if not backups[key].is_file():
                    raise FileNotFoundError(f'Backup {key} file does not exist')
        saved = []
        for key,path in selected.items():
            src,dst = (backups[key],path) if restore else (path,backups[key])
            if src.is_file():
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dst)
                saved.append(str(dst))
        return saved

    agent.tools.register('browser.reference','Capture a reference website into this output directory',
                         {'url':Parameter(str),'screenshot_path':Parameter(str)},reference)
    agent.tools.register('gui.backup','Back up HTML, CSS and screenshot without changing the page',
                         {'page_info':Parameter(dict)},backup)
    agent.tools.register('gui.restore','Restore the complete backed-up page',
                         {'page_info':Parameter(dict)},lambda page_info:backup(page_info,True))
    def clean():
        # Legacy clean also deletes backup directories. Preserve the GUI's undo
        # data and reference image while reusing its unused-image cleanup.
        protected=[root/'backup']
        reference=agent.task.get('img')
        if reference and Path(reference).is_file() and Path(reference).resolve().is_relative_to(root):
            protected.append(Path(reference).resolve())
        with tempfile.TemporaryDirectory() as staging:
            saved=[]
            for index,path in enumerate(protected):
                if path.exists():
                    target=Path(staging)/str(index)
                    (shutil.copytree if path.is_dir() else shutil.copy2)(path,target)
                    saved.append((path,target))
            try:
                agent.clean()
            finally:
                for path,target in saved:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    if target.is_dir():
                        shutil.copytree(target,path,dirs_exist_ok=True)
                    else:
                        shutil.copy2(target,path)
    agent.tools.register('gui.clean','Remove unused images while preserving backups and reference',{},clean)


def run_gui_tool(agent, tool, **parameters):
    allowed = {'browser.preview','browser.render','browser.reference','gui.backup','gui.restore','gui.clean'}
    if tool not in allowed:
        raise ToolValidationError('Unsupported GUI tool')
    if tool in ('browser.preview','browser.render'):
        root=Path(agent.save_file).resolve()
        for key in ('html_path','screenshot_path'):
            if key in parameters and not Path(parameters[key]).resolve().is_relative_to(root):
                raise ToolValidationError('Preview path escapes the output directory')
    base = agent._runtime()
    runtime = GuiToolRuntime(agent,storage_root=base.root,database_path=base.state.db.path,limits=base.limits)
    run_id = runtime.create_run(output_dir=agent.save_file,pages=deepcopy(agent.task_queue),
                                action={'method':'gui_tool','kwargs':{'tool':tool,'parameters':parameters}})

    async def execute():
        result = await runtime.execute(run_id)
        # A cancelled tool may still be draining a Selenium worker. Do not admit
        # the next GUI operation until it has released the shared browser.
        while runtime._pending:
            await asyncio.gather(*tuple(runtime._pending),return_exceptions=True)
        if result['status'] != 'completed':
            raise RunStopped(result,runtime.tracer.diagnostic_path(run_id))
        return runtime.state.tasks(run_id)[-1]['result'].get('value')
    return asyncio.run(execute())


def generate_or_resume(agent, pages, resume_id=None):
    """Resume only an unchanged whole-generation request, never a stale edit."""
    if resume_id:
        runtime = agent._runtime()
        record = runtime.state.get_run(resume_id)
        context = record['context']
        if (not context['settings'].get('action')
                and context['plan'] == pages
                and context['profile'] == {key:agent.task.get(key) for key in context['profile']}
                and context['feedback'] == (agent.user_feedback or '')
                and all(context['settings'].get(key) == getattr(agent,key) for key in
                        ('model','css_frame','vision','gen_img','language','status','industry','local_img_storage'))
                and Path(record['files']['output_dir']).resolve() == Path(agent.save_file).resolve()):
            result = asyncio.run(runtime.resume(resume_id))
            agent.last_run_id = resume_id
            agent.task_queue = deepcopy(result['context']['plan'] or [])
            if result['status'] != 'completed':
                raise RunStopped(result,runtime.tracer.diagnostic_path(resume_id))
            return deepcopy(agent.task_queue)
    if pages:
        asyncio.run(agent.deal_task_async(pages))
    else:
        agent.deal_task()
    return deepcopy(agent.task_queue)
