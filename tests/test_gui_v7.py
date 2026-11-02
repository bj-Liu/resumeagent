"""Run Tk on its own process main thread, isolated from async unit-test loops."""
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile


class GuiV7Tests(unittest.TestCase):
    def test_mock_workflow_and_main_thread_delivery(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,str(root/'tests/gui_v7_smoke.py')],cwd=root,
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
        self.assertIn('GUI_V7_MOCK_OK',result.stdout)

    def test_native_css_backup_restore_and_missing_backup_is_nondestructive(self):
        from PIL import Image
        from examples.harness_demo import DemoBrowser
        from harness.budget import BudgetLimits
        from harness.runtime import RunStopped
        from resumeagent.main import HomepageDesignAgent
        from resumeagent.frontend.harness_tools import run_gui_tool
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            agent=HomepageDesignAgent(save_file=str(root/'site'),llm=object(),browser=DemoBrowser(),
                runtime_options={'storage_root':str(root/'state'),'limits':BudgetLimits(max_retries=0)})
            agent.css_frame=None
            page={'html_name':'index.html','css_name':'site.css'}
            site=Path(agent.save_file)
            (site/'index.html').write_text('<html>before</html>',encoding='utf-8')
            (site/'site.css').write_text('body{color:red}',encoding='utf-8')
            Image.new('RGB',(4,4),'red').save(site/'index.png')
            original={path.name:path.read_bytes() for path in site.iterdir()}
            run_gui_tool(agent,'gui.backup',page_info=page)
            for name in original:
                (site/name).write_bytes(b'changed')
            run_gui_tool(agent,'gui.restore',page_info=page)
            for name,content in original.items():
                self.assertEqual((site/name).read_bytes(),content)
            (site/'backup/backup_site.css').unlink()
            (site/'index.html').write_text('keep this current content',encoding='utf-8')
            with self.assertRaises(RunStopped):
                run_gui_tool(agent,'gui.restore',page_info=page)
            self.assertEqual((site/'index.html').read_text(encoding='utf-8'),'keep this current content')
            self.assertEqual(agent._runtime().state.get_run(agent.last_run_id)['status'],'failed')
            agent.close()

    def test_gui_tools_reject_paths_outside_output_and_unknown_tools(self):
        from examples.harness_demo import DemoBrowser
        from harness.tools import ToolValidationError
        from resumeagent.main import HomepageDesignAgent
        from resumeagent.frontend.harness_tools import run_gui_tool
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            agent=HomepageDesignAgent(save_file=str(root/'site'),llm=object(),browser=DemoBrowser())
            for name,params in (('browser.preview',{'html_path':str(root/'private.html')}),('unknown',{})):
                with self.assertRaises(ToolValidationError):
                    run_gui_tool(agent,name,**params)
            agent.close()
