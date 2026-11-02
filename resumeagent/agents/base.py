"""Model delegation shared by all agent operations."""
import asyncio
from resumeagent.llm.client import LLMClient


class BaseAgent:
    def __init__(self, model='qwen3.8-flash', llm=None):
        self.model = model
        self.llm = llm if llm is not None else LLMClient()

    def act(self, instruction):
        raise NotImplementedError

    def get_LLM_response(self, messages, **kwargs):
        if kwargs.get('model') is None:
            kwargs['model'] = self.model
        from harness.context import CURRENT_EXECUTION
        scope = CURRENT_EXECUTION.get()
        if scope is not None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is scope.runtime.loop:
                raise RuntimeError('Use the async LLM method inside the Runtime event loop')
            return asyncio.run_coroutine_threadsafe(scope.runtime.llm_call(self,messages,kwargs),scope.runtime.loop).result()
        return self.llm.response(messages, **kwargs)

    async def get_LLM_response_async(self, messages, **kwargs):
        if kwargs.get('model') is None:
            kwargs['model'] = self.model
        from harness.context import CURRENT_EXECUTION
        scope = CURRENT_EXECUTION.get()
        if scope is not None:
            if asyncio.get_running_loop() is not scope.runtime.loop:
                future = asyncio.run_coroutine_threadsafe(scope.runtime.llm_call(self,messages,kwargs),scope.runtime.loop)
                return await asyncio.wrap_future(future)
            return await scope.runtime.llm_call(self, messages, kwargs)
        if hasattr(self.llm, 'response_async'):
            return await self.llm.response_async(messages, **kwargs)
        return await asyncio.to_thread(self.llm.response, messages, **kwargs)

    def get_answer(self, messages, **kwargs):
        return self.get_LLM_response(messages, **kwargs)

    async def get_answer_async(self, messages, **kwargs):
        return await self.get_LLM_response_async(messages, **kwargs)
