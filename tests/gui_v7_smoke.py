"""Real Tk + real Harness + Mock LLM/browser. Never calls a real model."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples.harness_demo import DemoLLM,DemoBrowser,DEMO_PAGES
from harness.context import CURRENT_EXECUTION
from harness.budget import BudgetLimits
from resumeagent.frontend.gui import Application
from resumeagent.main import HomepageDesignAgent
from resumeagent.llm import client


class Browser(DemoBrowser):
    def __init__(self):
        super().__init__()
        self.previews=[]
    def open_website(self,path):
        assert Path(path).is_file()
        self.previews.append(str(path))
    def get_screenshot(self,path,target,is_local=True):
        if not is_local:
            from PIL import Image
            Image.new('RGB',(400,300),'lavender').save(target)
            return
        return super().get_screenshot(path,target)


class GuiLLM(DemoLLM):
    async def response_async(self,messages,**kwargs):
        scope=CURRENT_EXECUTION.get()
        if scope.stage=='specification':
            action=scope.runtime.context.settings['action']
            if action['method']=='refine_page':
                page=deepcopy(action['args'][0]);page['description']='Refined specification'
                return '<modified_page>'+json.dumps(page)+'</modified_page>'
            page=deepcopy(action['args'][0][action['args'][1]])
            return '<completed_page>'+json.dumps(page)+'</completed_page><page_relationship>[]</page_relationship>'
        return await super().response_async(messages,**kwargs)


def run():
    parent=ROOT/'test-artifacts/gui-v7/mock'
    parent.mkdir(parents=True,exist_ok=True)
    events=[]
    main_thread=threading.get_ident()
    def popup(*args,**kwargs):
        assert threading.get_ident()==main_thread,'Worker called Tk dialog'
        events.append(args)
    with tempfile.TemporaryDirectory(dir=parent) as folder,patch('tkinter.messagebox.showerror',side_effect=popup),patch('tkinter.messagebox.showinfo',side_effect=popup):
        client.token_log_file=str(Path(folder)/'tokens.json')
        browser=Browser();backend=GuiLLM(needs_refinement=False)
        agent=HomepageDesignAgent(model='demo-model',save_file=str(Path(folder)/'site'),llm=backend,browser=browser,
                                  runtime_options={'storage_root':str(Path(folder)/'state'),'limits':BudgetLimits(max_iterations=1,max_retries=0)})
        old_cwd=Path.cwd()
        os.chdir(folder)
        try:
            app=Application(agent)
        finally:
            os.chdir(old_cwd)
        tk_errors=[]
        app.report_callback_exception=lambda *args:tk_errors.append(str(args[1]))
        app.update();app.withdraw();app.update()
        assert app.shared_background_path==ROOT/'gui_assets/shared_floral_background.png'
        assert app._shared_background_original is not None
        assert app._shared_background_photo is not None
        for name in ('display_table_page','update_cost','update_ui_after_refine_website'):
            original=getattr(app,name)
            def checked(*args,_original=original,**kwargs):
                assert threading.get_ident()==main_thread,'Worker updated Tk'
                return _original(*args,**kwargs)
            setattr(app,name,checked)
        entries=app.web_design_widgets['input_entries']
        for index,value in ((0,agent.save_file),(1,'Fictional GUI user'),(7,'1')):
            entries[index].insert(0,value)
        def wait():
            deadline=time.monotonic()+40
            while app.is_animating or (app._worker and app._worker.is_alive()):
                assert time.monotonic()<deadline,'GUI operation did not finish'
                app.update();time.sleep(.01)
            app.update()
            assert not tk_errors,tk_errors
        try:
            app.plan();app.plan() # duplicate request must be ignored
            wait();assert len(app.pages)==3 and not app.last_error,app.last_error
            assert sum(stage=='planning' for stage,_ in backend.calls)==4
            app.auto_gen_website();wait()
            generation_id=agent.last_run_id
            assert agent._runtime().state.get_run(generation_id)['status']=='completed'
            assert all(value=='completed' for value in app._page_states.values())
            assert (Path(agent.save_file)/'index.png').is_file()
            assert app._preview_source_image is not None
            app.next_page();assert app.current_page==1
            app.prev_page();assert app.current_page==0
            app.open_website();wait();assert browser.previews
            assert any(event['event']=='tool.completed' and event.get('tool')=='browser.preview' for event in agent._runtime().tracer.query(agent.last_run_id))
            app.create_website();wait();assert not app.last_error
            backup=Path(agent.save_file)/'backup/backup_index.html'
            assert backup.is_file()
            backup_bytes=backup.read_bytes()
            app.refine_website();wait();assert not app.last_error
            expected=backup.read_bytes()
            (Path(agent.save_file)/'index.html').write_text('<html>temporary change</html>',encoding='utf-8')
            app.restore_backup_html();wait()
            assert (Path(agent.save_file)/'index.html').read_bytes()==expected
            app.refine_page();wait();assert app.pages[0]['description']=='Refined specification'
            app.complete_page();wait();assert not app.last_error
            app.clean();wait();assert backup.exists()
            app.add_page();assert isinstance(app.pages[-1]['relationship'],dict)
            app.delete_page();assert len(app.pages)==3
            # Wrong type must not corrupt editor dictionaries or leave busy set.
            entries[7].delete(0,'end');entries[7].insert(0,'-1')
            app.auto_gen_website();assert not app.is_animating
            entries[7].delete(0,'end');entries[7].insert(0,'1')
            # Finite failure then GUI checkpoint resume, without regenerating successes.
            output=str(Path(folder)/'recovery')
            entries[0].delete(0,'end');entries[0].insert(0,output)
            backend.fail_page='projects.html';backend.fail_times=1
            app.auto_gen_website();wait()
            failed_id=app._resume_run_id
            assert failed_id and app.last_error and Path(app.last_error['diagnostic']).is_file()
            count_before=sum(stage=='generation' and name=='index.html' for stage,name in backend.calls)
            app.auto_gen_website();wait()
            assert agent.last_run_id==failed_id and not app.last_error
            assert sum(stage=='generation' and name=='index.html' for stage,name in backend.calls)==count_before
            # Keep real provider exception details redacted by Harness diagnostics.
            class PermissionDeniedError(Exception):
                pass
            async def denied(*args,**kwargs):
                raise PermissionDeniedError('AllocationQuota.FreeTierOnly: test account access denied')
            backend.response_async=denied
            app.refine_website();wait()
            assert app.last_error['type']=='PermissionDeniedError'
            assert 'AllocationQuota.FreeTierOnly' in app.last_error['message']
            assert app.last_error['run_id'] in events[-1][1]
            assert not tk_errors
            # Closing while a real worker is active must drain it without any
            # worker touching destroyed Tcl controls or showing late dialogs.
            before_close=len(events)
            app._start_operation('Closing test...',lambda:time.sleep(.15))
            app._on_close()
            deadline=time.monotonic()+10
            while not app._destroyed:
                assert time.monotonic()<deadline
                app.update();time.sleep(.01)
            assert not app._worker.is_alive() and len(events)==before_close
            summary={'mock_llm':True,'real_api_calls':0,'plan':True,'generate':True,'refine':True,'specification':True,
                     'complete':True,'page_switch':True,'preview':True,'backup_restore':True,'recovery':True,
                     'permission_error_diagnostics':True,'main_thread_ui':True,'shutdown_while_busy':True,'tk_errors':tk_errors}
            (parent.parent/'mock-result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print('GUI_V7_MOCK_OK',json.dumps(summary))
        finally:
            app.destroy();agent.close()


if __name__=='__main__':
    run()
