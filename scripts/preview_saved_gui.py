"""Restore an existing completed Run into the original Tk GUI, without executing it.

This is a read-only presentation utility, not a new GUI loading feature or a
generation demo. The original GUI and all business implementations stay intact.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tkinter as tk
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.tools import ToolRegistry
from resumeagent.frontend.gui import Application
from resumeagent.main import HomepageDesignAgent


class RequestsDisabled:
    def response(self, *args, **kwargs):
        raise RuntimeError('Saved-Run viewer cannot submit model requests')

    async def response_async(self, *args, **kwargs):
        raise RuntimeError('Saved-Run viewer cannot submit model requests')


def read_completed_run(database, run_id):
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None or row['status'] != 'completed':
            raise ValueError('A real completed Run is required')
        record = dict(row)
        record['context'] = json.loads(record['context'])
        record['usage'] = json.loads(record['usage'])
        record['files'] = json.loads(record['files'])
        pages = [dict(page) for page in conn.execute(
            'SELECT * FROM pages WHERE run_id=? ORDER BY position', (run_id,))]
        for page in pages:
            page['spec'] = json.loads(page['spec'])
        if not pages or any(page['status'] != 'completed' for page in pages):
            raise ValueError('Every displayed page must have a completed Page record')
    directory = Path(record['files']['output_dir']).resolve()
    for page in pages:
        name = Path(page['spec']['html_name'])
        for path in (directory / name, directory / name.with_suffix('.png')):
            if not path.is_file():
                raise FileNotFoundError(f'Missing saved artifact: {path.name}')
    return record, pages, directory


class SavedRunView(Application):
    """Original native controls, actual saved data, explicitly read-only."""
    def __init__(self, agent, preview_directory=None):
        self.preview_directory = preview_directory
        super().__init__(agent)

    def update_ui_after_refine_website(self):
        super().update_ui_after_refine_website()
        if self.pages and self.preview_directory:
            name = Path(self.pages[self.current_page]['html_name']).stem + '-1440.png'
            path = self.preview_directory / name
            if path.is_file():
                # Actual existing Edge viewport capture of the same final page.
                # Avoid upsampling the original long-page PNG, which the browser
                # intentionally downsized. Neither source image is overwritten.
                with Image.open(path) as image:
                    self._preview_source_image = image.convert('RGB')
                self._draw_creative_preview()

    def _prepare_operation(self, require_page=False):
        return False

    def _start_operation(self, *args, **kwargs):
        raise RuntimeError('Saved-Run viewer cannot execute workflow operations')

    def save_value(self, *args, **kwargs):
        return

    def create_blocks(self, frame):
        super().create_blocks(frame)
        # Presentation-only sizing: fit five real native page controls in the
        # existing list. No replacement dashboard or image-composed GUI.
        for button in self.buttons:
            button.master.configure(height=50)
            button.master.pack_configure(pady=(0, 5))
            button.pack_configure(padx=4, pady=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--refine-run-id')
    parser.add_argument('--proof', type=Path)
    parser.add_argument('--preview-dir', type=Path)
    args = parser.parse_args()
    record, pages, directory = read_completed_run(args.database, args.run_id)
    refinement = None
    if args.refine_run_id:
        refinement, _, refine_directory = read_completed_run(args.database, args.refine_run_id)
        if refine_directory != directory:
            raise ValueError('Refinement and generation must share the saved output directory')
    initial_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in directory.iterdir() if p.is_file()}
    database_hash = hashlib.sha256(args.database.read_bytes()).hexdigest()
    agent = HomepageDesignAgent(model=record['context']['settings']['model'],
                                save_file=str(directory), llm=RequestsDisabled())
    # No write or browser tools are exposed by this presentation-only session.
    agent.tools = ToolRegistry()
    app = SavedRunView(agent, args.preview_dir)
    settings = record['context']['settings']
    for key in ('model', 'language', 'status', 'industry', 'css_frame', 'gen_img'):
        if key in settings:
            setattr(agent, key, settings[key])
    agent.task = deepcopy(record['context']['profile'])
    agent.user_feedback = record['context']['feedback']
    agent.task_queue = [deepcopy(page['spec']) for page in pages]
    agent.last_run_id = args.run_id
    app.pages = deepcopy(agent.task_queue)
    app._page_states = {page['spec']['html_name']: page['status'] for page in pages}
    app.model_var.set(agent.model)
    app.language_var.set(agent.language)
    app.status_var.set(agent.status)
    app.industry_var.set(agent.industry)
    app.css_frame_var.set(agent.css_frame or 'None')
    app.gen_img_var.set('None' if not agent.gen_img else str(agent.gen_img))
    values = [str(directory), *[agent.task.get(k) or '' for k in
              ('basic_information', 'academic_achievements', 'experience', 'professional_skills')],
              agent.task.get('img') or '', agent.user_feedback,
              str(settings.get('refine_times', 1)), '']
    for entry, value in zip(app.web_design_widgets['input_entries'], values):
        entry.insert(0, value)
        entry.xview_moveto(0)
    app.display_table_page()
    page_holder = app.web_design_widgets['page_nav_frame'].master.master
    app.web_design_widgets['input_frame'].bind(
        '<Configure>', lambda event: page_holder.configure(height=300))
    page_holder.configure(height=300)
    app.title(f'ResumeAgent | Saved Run {args.run_id} | completed | read-only')
    app.animation_label.configure(text='Completed · saved Run')
    usage = record['usage']
    estimate = (usage['prompt_tokens'] * .8 + usage['completion_tokens'] * 2.7) / 1_000_000
    app.token_cost_label.configure(text=f'CNY {estimate:.4f}')
    app.time_label.configure(text=f'{record["elapsed"]:.1f} s')

    def protect(parent):
        for widget in parent.winfo_children():
            if isinstance(widget, tk.Button) and widget not in app.buttons:
                widget.configure(state=tk.DISABLED)
            if isinstance(widget, tk.Text):
                widget.bind('<Double-Button-1>', lambda event: 'break')
            protect(widget)
    protect(app)
    app.update_idletasks()
    if args.proof:
        args.proof.parent.mkdir(parents=True, exist_ok=True)
        args.proof.write_text(json.dumps({
            'source': 'Original Tkinter Application restored from read-only SQLite and actual output files',
            'generation_run': args.run_id, 'generation_status': record['status'],
            'refine_run': args.refine_run_id,
            'refine_status': refinement['status'] if refinement else None,
            'pages': [{'html_name': p['spec']['html_name'], 'status': p['status']} for p in pages],
            'mode': 'saved_result_viewer', 'new_model_calls': 0,
            'presentation_adjustment': 'Only native thumbnail cards compacted to fit the complete page list',
            'preview_source': 'Existing actual Edge viewport captures' if args.preview_dir else 'Existing generated page PNGs',
            'database_sha256_before': database_hash, 'artifact_sha256_before': initial_hashes,
        }, indent=2), encoding='utf-8')
    try:
        app.mainloop()
    finally:
        agent.close()
        assert hashlib.sha256(args.database.read_bytes()).hexdigest() == database_hash
        assert all(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
                   for name, digest in initial_hashes.items()), 'Viewer must never modify saved artifacts'


if __name__ == '__main__':
    main()
