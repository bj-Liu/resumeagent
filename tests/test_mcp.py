"""Real official-SDK protocol tests over memory streams and stdio; LLM/browser are mocks."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_client_server_memory_streams
from harness.jobs import JobManager
from harness.runtime import Runtime
from evals.support import load_cases, runtime_factory
from resumeagent.llm import client
from resumeagent.mcp_server import create_server

ROOT=Path(__file__).resolve().parents[1]


def value(result):
    return result.structuredContent or json.loads(result.content[0].text)


@asynccontextmanager
async def connected(manager):
    server=create_server(manager)
    async with create_client_server_memory_streams() as (client_streams,server_streams):
        running=asyncio.create_task(server.run(*server_streams,server.create_initialization_options()))
        try:
            async with ClientSession(*client_streams) as session:
                await session.initialize()
                yield session
        finally:
            running.cancel()
            await asyncio.gather(running,return_exceptions=True)
            await manager.aclose()


class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        patcher=patch.object(client,'token_log_file',str(self.root/'tokens.json'))
        patcher.start();self.addCleanup(patcher.stop)

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration=5

    def manager(self,**kwargs):
        return JobManager(storage_root=self.root,runtime_factory=lambda limits:runtime_factory(self.root,limits=limits),**kwargs)

    async def poll(self,session,run_id):
        for _ in range(400):
            result=await session.call_tool('get_generation_status',{'run_id':run_id})
            self.assertFalse(result.isError)
            status=value(result)
            if status['status'] in {'completed','failed','cancelled','budget_exceeded','timed_out'}:
                return status
            await asyncio.sleep(.01)
        self.fail('MCP job did not finish')

    async def test_official_client_create_status_and_preview(self):
        async with connected(self.manager()) as session:
            tools=await session.list_tools()
            self.assertEqual({t.name for t in tools.tools},{'generate_homepage','get_generation_status','preview_homepage'})
            created=await session.call_tool('generate_homepage',{'profile':{'basic_information':'Private example profile'},'max_iterations':1})
            self.assertFalse(created.isError)
            run_id=value(created)['run_id']
            status=await self.poll(session,run_id)
            self.assertEqual(status['status'],'completed')
            self.assertEqual(status['progress']['fraction'],1)
            self.assertNotIn('Private example profile',json.dumps(status))
            preview=await session.call_tool('preview_homepage',{'run_id':run_id,'page_id':status['pages'][0]['page_id']})
            self.assertFalse(preview.isError)
            self.assertTrue(value(preview)['available'])
            self.assertTrue(value(preview)['artifacts']['html']['uri'].startswith('file:///'))

    async def test_strict_inputs_and_private_error_redaction(self):
        async with connected(self.manager()) as session:
            for arguments in ({'profile':{}},{'profile':{'basic_information':123}},
                              {'profile':{'basic_information':'sk-SECRET','img':'C:/private.png'}},
                              {'profile':{'basic_information':'text'},'output_dir':'../escape'},
                              {'profile':{'basic_information':'text'},'max_iterations':True},
                              {'profile':{'basic_information':'x'*30001}}):
                result=await session.call_tool('generate_homepage',arguments)
                self.assertTrue(result.isError)
                self.assertEqual(value(result),{'error':'invalid_arguments'})
                self.assertNotIn('sk-SECRET',json.dumps(value(result)))
            result=await session.call_tool('get_generation_status',{'run_id':'../../config.yaml'})
            self.assertTrue(result.isError)

    async def test_unknown_runs_and_cross_run_page_access_are_denied(self):
        async with connected(self.manager()) as session:
            missing=await session.call_tool('get_generation_status',{'run_id':'0'*32})
            self.assertTrue(missing.isError)
            ids=[];statuses=[]
            for _ in range(2):
                run_id=value(await session.call_tool('generate_homepage',{'profile':{'basic_information':'Example'},'max_iterations':0}))['run_id']
                ids.append(run_id);statuses.append(await self.poll(session,run_id))
            mixed=await session.call_tool('preview_homepage',{'run_id':ids[0],'page_id':statuses[1]['pages'][0]['page_id']})
            self.assertTrue(mixed.isError)
            self.assertEqual(value(mixed),{'error':'not_found_or_not_permitted'})

    async def test_legacy_runs_and_escaped_artifacts_are_not_exposed(self):
        runtime=runtime_factory(self.root)
        legacy=runtime.create_run(load_cases()[0]['profile'])
        manager=self.manager()
        async with connected(manager) as session:
            denied=await session.call_tool('get_generation_status',{'run_id':legacy})
            self.assertTrue(denied.isError)
            run_id=value(await session.call_tool('generate_homepage',{'profile':{'basic_information':'Example'},'max_iterations':0}))['run_id']
            status=await self.poll(session,run_id)
            page_id=status['pages'][0]['page_id']
            secret=self.root/'private.html';secret.write_text('PRIVATE')
            with manager.reader.state.db.connect() as conn:
                conn.execute('UPDATE pages SET files=? WHERE id=?',(json.dumps({'html':str(secret)}),page_id))
            preview=await session.call_tool('preview_homepage',{'run_id':run_id,'page_id':page_id})
            self.assertTrue(preview.isError)

    async def test_admission_capacity_is_bounded(self):
        manager=self.manager(max_active=1,max_pending=1)
        manager.factory=lambda limits:runtime_factory(self.root,limits=limits,delay=.1)
        async with connected(manager) as session:
            first=await session.call_tool('generate_homepage',{'profile':{'basic_information':'Example'}})
            second=await session.call_tool('generate_homepage',{'profile':{'basic_information':'Example'}})
            self.assertFalse(first.isError);self.assertTrue(second.isError)
            self.assertEqual(value(second),{'error':'service_busy_or_unavailable'})

    async def test_stdio_subprocess_runs_with_real_official_client(self):
        params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'mcp/server.py'),'--mock','--storage-root',str(self.root/'stdio')],cwd=str(ROOT),env={'PYTHONIOENCODING':'cp1252'})
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                initialized=await session.initialize()
                self.assertIn('本地个人主页',initialized.instructions)
                created=await session.call_tool('generate_homepage',{'profile':{'basic_information':'Stdio Example'},'max_iterations':0})
                run_id=value(created)['run_id']
                status=await self.poll(session,run_id)
                self.assertEqual(status['status'],'completed')
                preview=await session.call_tool('preview_homepage',{'run_id':run_id,'page_id':status['pages'][0]['page_id']})
                self.assertTrue(value(preview)['available'])
        reader=Runtime(storage_root=self.root/'stdio')
        self.assertEqual(reader.generation_status(run_id,origin='mcp')['status'],'completed')


if __name__=='__main__':
    unittest.main()
