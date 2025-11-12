from openai import AzureOpenAI, OpenAI,AsyncAzureOpenAI,AsyncOpenAI
from anthropic import Anthropic,AsyncAnthropic
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
import dashscope
from zhipuai import ZhipuAI
from dashscope import Generation
from dashscope.aigc.generation import AioGeneration
from dashscope import MultiModalConversation
from abc import abstractmethod  
from http import HTTPStatus 
import platform
import dashscope
import yaml 
import os
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
for key, value in config.items():   
    os.environ[key] = str(value)
import httpx
import logging   
import json
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
)
import asyncio
import requests
from PIL import Image
from io import BytesIO
from utils import fetch_image,get_openai_url,encode_image
from dashscope import MultiModalConversation



def before_retry_fn(retry_state):
    if retry_state.attempt_number > 1:  
        logging.info(f"Retrying API call. Attempt #{retry_state.attempt_number}, f{retry_state}")
token_log_file = os.environ.get("TOKEN_LOG_FILE", "logs/token.json")


class base_llm: 
    def __init__(self) -> None:
        pass
    
    @abstractmethod  
    def response(self,messages,**kwargs):  
        pass

    def get_imgs(self,prompt, save_path="saves/dalle3.jpg"):   
        pass

class base_img_llm(base_llm):  
    def __init__(self) -> None:
        pass

    @abstractmethod
    def get_img(self,prompt, save_path="saves/dalle3.jpg"):
        pass


class openai_llm(base_llm):
    def __init__(self) -> None:
        super().__init__()    
        is_azure = config.get("is_azure", True) 
        if is_azure:
            if "AZURE_OPENAI_ENDPOINT" not in os.environ or os.environ["AZURE_OPENAI_ENDPOINT"] == "":
                raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
            if "AZURE_OPENAI_KEY" not in os.environ or os.environ["AZURE_OPENAI_KEY"] == "":
                raise ValueError("AZURE_OPENAI_KEY is not set")
            
            api_version = os.environ.get("AZURE_OPENAI_API_VERSION",None)
            if api_version == "":
                api_version = None
            self.client = AzureOpenAI(  
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], 
                api_key=os.environ["AZURE_OPENAI_KEY"],
                api_version= api_version   
                )
            self.async_client = AsyncAzureOpenAI(  
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_KEY"],
                api_version= api_version
                )      

        else:
            if "OPENAI_API_KEY" not in os.environ or os.environ["OPENAI_API_KEY"] == "":
                raise ValueError("OPENAI_API_KEY is not set")
            
            api_key = os.environ.get("OPENAI_API_KEY",None)
            proxy_url = os.environ.get("OPENAI_PROXY_URL", None)
            if proxy_url == "":
                proxy_url = None
            base_url = os.environ.get("OPENAI_BASE_URL", None)
            if base_url == "":
                base_url = None
            http_client = httpx.Client(proxy=proxy_url) if proxy_url else None    
            async_http_client = httpx.AsyncClient(proxy=proxy_url) if proxy_url else None

            self.client = OpenAI(api_key=api_key,base_url=base_url,http_client=http_client)  

            self.async_client = AsyncOpenAI(api_key=api_key,base_url=base_url,http_client=async_http_client)
    
    def process_messages(self, messages):  
        new_messages = []
        for message in messages:
            if message["role"] == "user":
                content = message["content"]
                if isinstance(content, list):  
                    new_content= []
                    for c in content:
                        if c["type"] == "image":
                            new_content.append({"type":"image_url","image_url":{"url":get_openai_url(c["url"]),"detail":"high"}})
                        else:
                            new_content.append(c)
                    new_messages.append({"role":"user","content":new_content})
                else:
                    new_messages.append(message)
            else:
                new_messages.append(message)
        return new_messages
    
    @retry(wait=wait_fixed(10), stop=stop_after_attempt(10), before=before_retry_fn)

    def response(self,messages,**kwargs):
        messages = self.process_messages(messages)  
        try:        
            response = self.client.chat.completions.create(
                model=kwargs.get("model", "gpt-4o-mini"),
                messages=messages,
                n = kwargs.get("n", 1), 
                temperature= kwargs.get("temperature", 0.3),  
                top_p=0.7,
                max_tokens=kwargs.get("max_tokens", 4000), 
                timeout=kwargs.get("timeout", 180)  
            )
        except Exception as e:  
            model = kwargs.get("model", "gpt-4o-mini")
            print(f"get {model} response failed: {e}")
            logging.info(e) 
            return
        
        if not os.path.exists(token_log_file):
            with open(token_log_file, "w") as f:
                json.dump({},f) 
        with open(token_log_file, "r") as f:
            tokens = json.load(f)
            current_model = kwargs.get("model", "gpt-4o-mini")
            if current_model not in tokens:
                tokens[current_model] = [0,0]
            tokens[current_model][0] += response.usage.prompt_tokens      
            tokens[current_model][1] += response.usage.completion_tokens
        with open(token_log_file, "w") as f:
            json.dump(tokens, f)

        return response.choices[0].message.content  


class qwen_llm(base_llm): 
    def __init__(self) -> None:
        super().__init__()
        if "DASHSCOPE_API_KEY" not in os.environ or os.environ["DASHSCOPE_API_KEY"] == "":
            raise ValueError("DASHSCOPE_API_KEY is not set")
        dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]
    
    def process_messages(self, messages):  
        new_messages = []
        for message in messages:
            if message["role"] == "user":
                content = message["content"]
                if isinstance(content, list): 
                    new_content= []
                    for c in content:
                        if c["type"] == "image":
                            new_content.append({"type":"image_url","image_url":{"url":get_openai_url(c["url"]),"detail":"high"}})
                        else:
                            new_content.append(c)
                    new_messages.append({"role":"user","content":new_content})
                else:
                    new_messages.append(message)
            else:
                new_messages.append(message)  
        return new_messages
    
    @retry(wait=wait_fixed(10), stop=stop_after_attempt(10), before=before_retry_fn, reraise=True)
    def response(self, messages, **kwargs):
        messages = self.process_messages(messages)
        try:    
            response = Generation.call(
                model = kwargs.get("model", "qwen3-max"),
                messages = messages,
                top_p = 0.7,
                temperature = 0.3,
                result_format = "message"
            )
        except Exception as e:
            model = kwargs.get("model", "qwen3-max")
            print(f"get {model} response failed: {e}")
            print(e)
            logging.info(e)
            return
        if not os.path.exists(token_log_file):
            with open(token_log_file, "w") as f:
                json.dump({},f)
        with open(token_log_file, "r") as f:
            tokens = json.load(f)
            current_model = kwargs.get("model", "qwen3-max")
            if current_model not in tokens:
                tokens[current_model] = [0,0]
            tokens[current_model][0] += response.usage.input_tokens
            tokens[current_model][1] += response.usage.output_tokens
        with open(token_log_file, "w") as f:
            json.dump(tokens, f)
        return response.output.choices[0].message.content
     

def get_llm():
    llm_type = config.get("LLM_TYPE", "openai")
    llm = None
    if llm_type in ["openai"]:
        llm = openai_llm()
    elif llm_type == "qwen":
        llm = qwen_llm()
    else:
        raise ValueError(f"Unknown LLM type: {llm_type}")
    return llm
    
if __name__ == "__main__":
    llm = get_llm()
    prompt = "简洁的简历模板，包含个人信息、工作经验和教育背景的分区"
    img_llm.get_img(prompt,"resume_template.jpg")






