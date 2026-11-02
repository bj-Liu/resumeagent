"""Configuration and compatible OpenAI/Azure/Qwen model adapters."""
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from threading import RLock
from contextvars import ContextVar
from resumeagent.config import PROJECT_ROOT, config
from resumeagent.tools.filesystem_helpers import atomic_write, get_openai_url

token_log_file = os.environ.get('TOKEN_LOG_FILE', str(PROJECT_ROOT / 'logs/token.json'))
_token_lock = RLock()
usage_observer = ContextVar('resumeagent_usage_observer', default=None)


def read_tokens():
    with _token_lock:
        path = Path(token_log_file)
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def record_tokens(model, prompt, completion):
    with _token_lock:
        tokens = read_tokens()
        usage = tokens.setdefault(model, [0, 0])
        usage[0] += prompt
        usage[1] += completion
        path = Path(token_log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(tokens))
    observer = usage_observer.get()
    if observer is not None:
        observer(model, prompt, completion)


def before_retry_fn(retry_state):
    import logging
    if retry_state.attempt_number > 1:
        logging.info('Retrying API call. Attempt #%s', retry_state.attempt_number)


class base_llm:
    def response(self, messages, **kwargs):
        raise NotImplementedError

    async def response_async(self, messages, **kwargs):
        return await asyncio.to_thread(self.response, messages, **kwargs)

    def process_messages(self, messages):
        result = []
        for message in messages:
            message = dict(message)
            if isinstance(message.get('content'), list):
                content = []
                for block in message['content']:
                    if block.get('type') == 'image':
                        url = str(block['url'])
                        if not url.startswith(('http://', 'https://', 'data:')):
                            url = get_openai_url(url)
                        content.append({'type': 'image_url', 'image_url': {'url': url, 'detail': 'high'}})
                    else:
                        content.append(dict(block))
                message['content'] = content
            result.append(message)
        return result


class openai_llm(base_llm):
    def __init__(self):
        from openai import OpenAI, AzureOpenAI, AsyncOpenAI, AsyncAzureOpenAI
        import httpx
        is_azure = os.environ.get('is_azure', str(config.get('is_azure', True))).lower() == 'true'
        if is_azure:
            params = dict(azure_endpoint=os.environ.get('AZURE_OPENAI_ENDPOINT'),
                          api_key=os.environ.get('AZURE_OPENAI_KEY'),
                          api_version=os.environ.get('AZURE_OPENAI_API_VERSION') or None)
            if not params['azure_endpoint'] or not params['api_key']:
                raise ValueError('AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY is not set')
            self.client = AzureOpenAI(**params)
            self.async_client = AsyncAzureOpenAI(**params)
        else:
            params = dict(api_key=os.environ.get('OPENAI_API_KEY'), base_url=os.environ.get('OPENAI_BASE_URL') or None)
            if not params['api_key']:
                raise ValueError('OPENAI_API_KEY is not set')
            proxy = os.environ.get('OPENAI_PROXY_URL')
            self.client = OpenAI(**params, http_client=httpx.Client(proxy=proxy) if proxy else None)
            self.async_client = AsyncOpenAI(**params, http_client=httpx.AsyncClient(proxy=proxy) if proxy else None)

    def _params(self, messages, kwargs):
        return dict(model=kwargs.get('model', 'gpt-4o-mini'), messages=self.process_messages(messages),
                    n=kwargs.get('n', 1), temperature=kwargs.get('temperature', .3),
                    top_p=kwargs.get('top_p', .7), max_tokens=kwargs.get('max_tokens', 4000),
                    timeout=kwargs.get('timeout', 180))

    def _content(self, response, model):
        if response.usage:
            record_tokens(model, response.usage.prompt_tokens, response.usage.completion_tokens)
        return response.choices[0].message.content

    def response(self, messages, **kwargs):
        params = self._params(messages, kwargs)
        client = self.client.with_options(max_retries=0) if kwargs.get('_max_attempts') == 1 else self.client
        return self._content(client.chat.completions.create(**params), params['model'])

    async def response_async(self, messages, **kwargs):
        params = self._params(messages, kwargs)
        client = self.async_client.with_options(max_retries=0) if kwargs.get('_max_attempts') == 1 else self.async_client
        response = await client.chat.completions.create(**params)
        return self._content(response, params['model'])



class qwen_llm(base_llm):
    def __init__(self):
        import dashscope

        key = os.environ.get("DASHSCOPE_API_KEY")
        if not key:
            raise ValueError("DASHSCOPE_API_KEY is not set")

        self.api_key = key
        self.dashscope = dashscope

        # Beijing region
        client_kwargs = {
            "api_key": key,
            "region": os.environ.get("DASHSCOPE_REGION", "cn-beijing"),
        }

        # Optional: Bailian Workspace ID
        workspace = os.environ.get("DASHSCOPE_WORKSPACE_ID")
        if workspace:
            client_kwargs["workspace"] = workspace

        self.client = dashscope.Client(**client_kwargs)

    def _convert_messages(self, messages):
        converted = []

        for message in messages:
            role = message["role"]
            content = message.get("content", "")

            # Tool messages use string content
            if role == "tool":
                converted.append({
                    "role": role,
                    "content": str(content)
                })
                continue

            # Convert text-only messages
            if isinstance(content, str):
                content = [{"text": content}]

            blocks = []

            for block in content:
                block_type = block.get("type")

                if block_type == "text":
                    blocks.append({
                        "text": block["text"]
                    })

                elif block_type in ("image", "image_url"):
                    if block_type == "image_url":
                        image_url = block["image_url"]
                        url = (
                            image_url["url"]
                            if isinstance(image_url, dict)
                            else image_url
                        )
                    else:
                        url = block.get("url", block.get("image"))

                    if not url:
                        raise ValueError("Image URL is missing")

                    url = str(url)

                    # HTTP URL or Base64 data URI
                    if url.startswith(("http://", "https://", "data:")):
                        image = url

                    # Convert file URI to local absolute path
                    elif url.startswith("file://"):
                        parsed = urlparse(url)
                        image = unquote(parsed.path)

                        if parsed.netloc:
                            image = f"//{parsed.netloc}{image}"
                        elif os.name == 'nt' and len(image) > 2 and image[0] == '/' and image[2] == ':':
                            image = image[1:]

                    # Local image path
                    else:
                        image = str(Path(url).resolve())

                    # Inline ordinary local screenshots via the inference endpoint.
                    # The SDK's separate OSS uploader can fail behind a proxy even
                    # when model requests work. Keep its path for large images so
                    # inline encoding never exceeds the service's 20 MB limit.
                    if not image.startswith(('http://', 'https://', 'data:', 'oss://')):
                        local_image = Path(image)
                        if local_image.is_file() and local_image.stat().st_size <= 14 * 1024 * 1024:
                            image = get_openai_url(local_image)

                    blocks.append({
                        "image": image
                    })

                else:
                    raise ValueError(
                        f"Unsupported message content type: {block_type}"
                    )

            converted.append({
                "role": role,
                "content": blocks
            })

        return converted


    def response(self, messages, **kwargs):
        from tenacity import Retrying, stop_after_attempt, wait_fixed

        model = kwargs.get("model", "qwen3.8-flash")

        converted = self._convert_messages(messages)

        for attempt in Retrying(
            stop=stop_after_attempt(kwargs.get('_max_attempts', 3)),
            wait=wait_fixed(2),
            reraise=True,
            before=before_retry_fn
        ):
            with attempt:
                api_client = self.client.with_options(max_retries=0) if kwargs.get('_max_attempts') == 1 else self.client
                response = api_client.multimodal.chat.create(
                    model=model,
                    messages=converted,

                    # Generation parameters
                    temperature=kwargs.get("temperature", 0.3),
                    top_p=kwargs.get("top_p", 0.7),

                    # Disable unnecessary reasoning for now
                    enable_thinking=kwargs.get("enable_thinking", False),
                    parameters={'preserve_thinking': kwargs['preserve_thinking']} if 'preserve_thinking' in kwargs else None,
                    timeout=kwargs.get('timeout', 180),
                )

                # Account for the provider response even if parsing fails afterwards.
                usage = response.usage
                if usage:
                    record_tokens(
                        model,
                        usage.input_tokens,
                        usage.output_tokens
                    )

                # Client 2.x returns a flat ChatCompletion, unlike legacy responses.
                choices = getattr(response, 'choices', None)
                if choices is None:
                    choices = getattr(getattr(response, 'output', None), 'choices', None)
                if not choices:
                    raise ValueError('Qwen response contains no choices')
                content = choices[0].message.content

                if isinstance(content, list):
                    return "".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict)
                    )

                return content


def get_llm():
    kind = os.environ.get('LLM_TYPE', config.get('LLM_TYPE', 'openai'))
    if kind == 'openai':
        return openai_llm()
    if kind == 'qwen':
        return qwen_llm()
    raise ValueError(f'Unknown LLM type: {kind}')


class LLMClient:
    """Lazy facade lets the GUI start before a backend is configured."""
    def __init__(self):
        self._backend = None
        self._lock = RLock()

    @property
    def backend(self):
        with self._lock:
            if self._backend is None:
                self._backend = get_llm()
            return self._backend

    def response(self, messages, **kwargs):
        return self.backend.response(messages, **kwargs)

    async def response_async(self, messages, **kwargs):
        return await self.backend.response_async(messages, **kwargs)
