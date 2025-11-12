
from LLM import get_llm

Openai_Models = ["gpt-35-turbo-16k","gpt-4-turbo-2024-04-09"]  
Qwen_Models = ["qwen3-max","qwen2-72b-instruct"]

class BaseAgent:
    def __init__(self,model = "qwen3-max") -> None:
        self.model = model
        self.llm = get_llm()
    
    def act(self, instruction):     
        raise NotImplementedError
    
    def get_LLM_response(self, messages, **kwargs):
        if kwargs.get("model") is None:
            kwargs["model"] = self.model
        if hasattr(self.llm, "response"):
            return self.llm.response(messages, **kwargs)
        raise RuntimeError("LLM does not support synchronous response()")

    async def get_LLM_response_async(self, messages, **kwargs):
        if kwargs.get("model") is None:
            kwargs["model"] = self.model
        if hasattr(self.llm, "response_async"):
            return await self.llm.response_async(messages, **kwargs)
        if hasattr(self.llm, "response"):
            return self.llm.response(messages, **kwargs)
        raise RuntimeError("LLM does not support response_async() or response()")

    def get_answer(self, messages, **kwargs):
        return self.get_LLM_response(messages, **kwargs)

    async def get_answer_async(self, messages, **kwargs):
        return await self.get_LLM_response_async(messages, **kwargs)


