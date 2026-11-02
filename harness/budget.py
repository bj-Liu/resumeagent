"""Per-run resource accounting and admission limits; pricing reuses legacy estimates."""
import asyncio
from dataclasses import asdict, dataclass
import math
from threading import RLock
import time
from resumeagent.utils import cal_cost
from .state import now


class BudgetExceeded(RuntimeError):
    pass


class RunCancelled(RuntimeError):
    pass


class RequestTimedOut(RuntimeError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    max_cost: float | None = None
    max_prompt_tokens: int | None = None
    max_completion_tokens: int | None = None
    max_iterations: int = 2
    max_concurrency: int = 3
    request_timeout: float = 180
    max_run_seconds: float = 1800
    max_retries: int = 2
    # Optional provider-specific USD rates per million tokens.
    prices: dict | None = None

    def __post_init__(self):
        for name in ('max_iterations', 'max_retries', 'max_concurrency', 'max_prompt_tokens', 'max_completion_tokens'):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < (1 if name == 'max_concurrency' else 0)):
                raise ValueError(f'Invalid {name}')
        for name in ('max_cost', 'request_timeout', 'max_run_seconds'):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0 or (name != 'max_cost' and value == 0)):
                raise ValueError(f'Invalid {name}')
        for rates in (self.prices or {}).values():
            if len(rates) != 2 or any(not math.isfinite(v) or v < 0 for v in rates):
                raise ValueError('Prices require two nonnegative rates per million tokens')

    def to_dict(self):
        return asdict(self)


class Budget:
    def __init__(self, state, tracer, run_id, limits):
        self.state, self.tracer, self.run_id, self.limits = state, tracer, run_id, limits
        self.slots = asyncio.Semaphore(limits.max_concurrency)
        self._lock = RLock()
        self._started = time.monotonic()
        self._prior_elapsed = state.get_run(run_id)['elapsed']
        self.stopped = None
        self.pending_requests = 0
        self.pending_tools = 0

    @property
    def elapsed(self):
        return self._prior_elapsed + time.monotonic() - self._started

    def usage(self):
        with self.state.db.connect() as conn:
            row = conn.execute('SELECT COALESCE(SUM(prompt_tokens),0) p,COALESCE(SUM(completion_tokens),0) c,COALESCE(SUM(cost),0) cost FROM usage_events WHERE run_id=?', (self.run_id,)).fetchone()
        return {'prompt_tokens': row['p'], 'completion_tokens': row['c'], 'cost': row['cost'],
                'cost_source': 'configured_or_legacy_estimate', 'pending_requests': self.pending_requests, 'pending_tools': self.pending_tools}

    def check(self):
        if self.stopped:
            raise self.stopped
        if self.state.get_run(self.run_id)['cancel_requested']:
            self.stopped = RunCancelled('Run cancelled')
            raise self.stopped
        usage = self.usage()
        if self.elapsed >= self.limits.max_run_seconds:
            self.stopped = BudgetExceeded('max_run_seconds')
        elif self.limits.max_cost is not None and usage['cost'] >= self.limits.max_cost:
            self.stopped = BudgetExceeded('max_cost')
        elif self.limits.max_prompt_tokens is not None and usage['prompt_tokens'] >= self.limits.max_prompt_tokens:
            self.stopped = BudgetExceeded('max_prompt_tokens')
        elif self.limits.max_completion_tokens is not None and usage['completion_tokens'] >= self.limits.max_completion_tokens:
            self.stopped = BudgetExceeded('max_completion_tokens')
        if self.stopped:
            raise self.stopped

    def record(self, request_id, model, prompt_tokens, completion_tokens):
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError('Invalid token usage')
        rates = (self.limits.prices or {}).get(model)
        cost = (prompt_tokens*rates[0] + completion_tokens*rates[1])/1_000_000 if rates else cal_cost(prompt_tokens, completion_tokens, model)
        with self._lock:
            with self.state.db.connect() as conn:
                conn.execute('INSERT INTO usage_events(run_id,request_id,model,prompt_tokens,completion_tokens,cost,timestamp) VALUES(?,?,?,?,?,?,?)',
                             (self.run_id,request_id,model,prompt_tokens,completion_tokens,cost,now()))
            self.state.update_run(self.run_id, usage=self.usage())
            self.tracer.emit(self.run_id, 'llm.usage', request_id=request_id, model=model,
                             prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost=cost,
                             cost_source='configured' if rates else 'legacy_estimate')

    def snapshot(self):
        self.state.update_run(self.run_id, elapsed=self.elapsed, usage=self.usage())
