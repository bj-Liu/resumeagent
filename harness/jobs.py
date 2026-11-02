"""Bounded background Run ownership for local protocol interfaces."""
import asyncio
from dataclasses import replace
from pathlib import Path
import re
from .budget import BudgetLimits
from .runtime import Runtime

ID_PATTERN = re.compile(r'^[0-9a-f]{32}$')
DEFAULT_MCP_LIMITS = BudgetLimits(
    max_cost=1, max_iterations=3, max_concurrency=2,
    max_run_seconds=600, request_timeout=120,
)


class JobManager:
    def __init__(self, *, storage_root, runtime_factory=None, limits=None, max_active=2, max_pending=4):
        if not 1 <= max_active <= max_pending <= 32:
            raise ValueError('Invalid job capacity')
        self.root = Path(storage_root).resolve()
        self.limits = limits or DEFAULT_MCP_LIMITS
        self.factory = runtime_factory or (lambda limits:Runtime.configured(storage_root=self.root,limits=limits))
        self.reader = Runtime(storage_root=self.root)
        self.slots = asyncio.Semaphore(max_active)
        self.max_pending = max_pending
        self.jobs = {}
        self.closed = False

    @staticmethod
    def validate_id(value):
        if not isinstance(value,str) or not ID_PATTERN.fullmatch(value):
            raise ValueError('Invalid identifier')

    async def submit(self, profile, feedback='', language='en', max_iterations=2):
        if self.closed or len(self.jobs) >= self.max_pending:
            raise RuntimeError('Generation service capacity reached')
        if type(max_iterations) is not int or not 0 <= max_iterations <= self.limits.max_iterations:
            raise ValueError('Requested iterations exceed server limit')
        if language not in ('en','zh'):
            raise ValueError('Invalid language')
        runtime = self.factory(replace(self.limits,max_iterations=max_iterations))
        # Runtime owns the session and all subsequent business operations.
        run_id = runtime.create_run(profile,feedback=feedback,origin='mcp',language=language)
        task = asyncio.create_task(self._execute(runtime,run_id))
        self.jobs[run_id] = (runtime,task)
        task.add_done_callback(lambda finished:self._finished(run_id,finished))
        return {'run_id':run_id,'status':'created','execution_mode':runtime.state.get_run(run_id)['context']['settings'].get('execution_mode','live')}

    def _finished(self, run_id, task):
        self.jobs.pop(run_id,None)
        if not task.cancelled():
            task.exception()  # All error details are already sanitized in Runtime state/tracing.

    async def _execute(self, runtime, run_id):
        try:
            async with self.slots:
                await runtime.execute(run_id)
        except asyncio.CancelledError:
            runtime.cancel(run_id)
            raise
        except Exception as exc:
            from .tracing import safe_error
            runtime.state.update_run(run_id,status='failed',error=safe_error(exc))
            runtime.tracer.emit(run_id,'job.failed',error=safe_error(exc),status='failed')
        finally:
            await runtime.aclose()

    def status(self, run_id):
        self.validate_id(run_id)
        return self.reader.generation_status(run_id,origin='mcp')

    def preview(self, run_id, page_id):
        self.validate_id(run_id); self.validate_id(page_id)
        return self.reader.preview_page(run_id,page_id,origin='mcp')

    async def aclose(self):
        self.closed = True
        for run_id,(runtime,_) in list(self.jobs.items()):
            if runtime.state.get_run(run_id)['status'] in ('created','running'):
                runtime.cancel(run_id)
        await asyncio.gather(*(task for _,task in list(self.jobs.values())),return_exceptions=True)
