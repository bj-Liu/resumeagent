"""Bounded stage inputs and task-local execution identity (safe across asyncio/to_thread)."""
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass

CURRENT_EXECUTION = ContextVar('resumeagent_execution', default=None)


@dataclass(frozen=True)
class ExecutionScope:
    runtime: object
    run_id: str
    task_id: str
    page_id: str
    stage: str
    agent: str


class Context:
    def __init__(self, profile=None, feedback='', plan=None, settings=None):
        self.profile = deepcopy(profile or {})
        self.feedback = feedback or ''
        self.plan = deepcopy(plan)
        self.settings = deepcopy(settings or {})

    def to_dict(self):
        return deepcopy({'profile': self.profile, 'feedback': self.feedback, 'plan': self.plan, 'settings': self.settings})

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def build(self, stage, page=None):
        data = {'stage': stage, 'feedback': self.feedback}
        if stage in {'planning', 'generation', 'refinement'}:
            data['profile'] = deepcopy(self.profile)
        if stage in {'planning', 'generation'}:
            data['website_plan'] = deepcopy(self.plan)
        if page:
            data['page_spec'] = deepcopy(page['spec'])
            if stage in {'evaluation', 'refinement', 'validation', 'rendering'}:
                data['artifacts'] = deepcopy(page['files'])
            if stage == 'refinement':
                data['history'] = deepcopy(page['checkpoint'].get('history', [])[-2:])
        return data
