"""Official SDK stdio Client example. Default mock mode makes no paid API requests."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {'completed','failed','cancelled','budget_exceeded','timed_out'}


def structured(result):
    if result.isError:
        raise RuntimeError(result.content[0].text)
    return result.structuredContent or json.loads(result.content[0].text)


async def run(args):
    arguments = [str(ROOT/'mcp'/'server.py'),'--storage-root',str(Path(args.storage_root).resolve())]
    if not args.live:
        arguments.append('--mock')
    elif args.browser:
        arguments += ['--browser',args.browser]
    forwarded = {key:value for key,value in os.environ.items() if key in ('RESUMEAGENT_CONFIG','OPENAI_API_KEY','OPENAI_BASE_URL','OPENAI_PROXY_URL','AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_KEY','AZURE_OPENAI_API_VERSION','DASHSCOPE_API_KEY','DASHSCOPE_REGION','DASHSCOPE_WORKSPACE_ID','WEBDRIVER_PATH','SE_CACHE_PATH','SE_TIMEOUT','SE_AVOID_STATS')}
    params = StdioServerParameters(command=sys.executable,args=arguments,cwd=str(ROOT),env=forwarded)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            listed = await session.list_tools()
            print('Tools:',', '.join(t.name for t in listed.tools))
            created = structured(await session.call_tool('generate_homepage',{'profile':{
                'basic_information':'MCP Example, fictional software engineer.',
                'experience':'Created an accessible website.'},'max_iterations':1}))
            run_id = created['run_id']; print('Run:',run_id)
            for _ in range(2400):
                status = structured(await session.call_tool('get_generation_status',{'run_id':run_id}))
                if status['status'] in TERMINAL:
                    break
                await asyncio.sleep(.25)
            else:
                raise TimeoutError('Polling timed out')
            print(json.dumps(status,ensure_ascii=False,indent=2))
            if status['status'] != 'completed':
                return 1
            preview = structured(await session.call_tool('preview_homepage',{'run_id':run_id,'page_id':status['pages'][0]['page_id']}))
            print('Preview:',json.dumps(preview,ensure_ascii=False,indent=2))
            return 0


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--storage-root',default=str(ROOT/'test-artifacts'/'mcp-example'))
    parser.add_argument('--live',action='store_true',help='Use configured real LLM; may incur API charges')
    parser.add_argument('--browser',choices=['edge','chrome','firefox'])
    raise SystemExit(asyncio.run(run(parser.parse_args())))
