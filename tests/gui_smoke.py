"""Isolated real Tk startup/input test: keep Tk destruction on the main thread."""
import gc
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resumeagent.main import HomepageDesignAgent
from resumeagent.frontend.gui import Application


def main():
    with tempfile.TemporaryDirectory() as directory:
        agent=HomepageDesignAgent(save_file=directory)
        selected_model=agent.model
        app=Application(agent=agent)
        try:
            app.withdraw();app.update_idletasks()
            assert agent.model==selected_model
            assert app.model_var.get()==selected_model
            app.is_animating=True
            app.animate(['Planning one','Planning two','Planning three'])
            old_animation=app._animation_after_id
            app.animation_idx=2
            app.animate(['Generating through Harness Runtime...'])
            assert app.animation_label.cget('text')=='Generating through Harness Runtime...'
            assert app.animation_idx==0
            assert old_animation not in app.tk.call('after','info')
            new_animation=app._animation_after_id
            app.is_animating=False
            app.animate(['Generating through Harness Runtime...'])
            assert new_animation not in app.tk.call('after','info')
            entries=app.web_design_widgets['input_entries']
            for index,text in ((0,directory),(2,'Research'),(8,directory)):
                entries[index].delete(0,'end');entries[index].insert(0,text)
            app.read_input_entries()
            assert agent.task['academic_achievements']=='Research'
            assert agent.local_img_storage_path==directory
            app.pages=[{'html_name':'index.html','is_main_page':True,'relationship':{'links':[]}}]
            app._save_pages(directory)
            assert json.loads((Path(directory)/'pages.json').read_text(encoding='utf-8'))==app.pages
            # The child owns this Tcl command. Root teardown must not delete it
            # twice when cancelling pending callbacks.
            app.web_design_widgets['input_frame'].after(10000,lambda:None)
        finally:
            app.destroy()
            del app
            gc.collect()
            agent.close()
    print('GUI_SMOKE_OK')


if __name__=='__main__':
    main()
