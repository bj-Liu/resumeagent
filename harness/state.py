"""Durable Run/Task/Page checkpoints with transactional transitions."""
from datetime import datetime, timezone
import json
import time
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False)


def decode(row):
    if row is None:
        raise KeyError('State record does not exist')
    result = dict(row)
    for key in ('context', 'limits', 'usage', 'files', 'spec', 'checkpoint', 'result', 'data'):
        if key in result:
            result[key] = json.loads(result[key])
    return result


class StateStore:
    def __init__(self, database):
        self.db = database

    def create_run(self, context, limits, files):
        run_id = uuid4().hex
        timestamp = now()
        with self.db.connect() as conn:
            conn.execute('INSERT INTO runs(id,status,stage,created_at,updated_at,context,limits,files) VALUES(?,?,?,?,?,?,?,?)',
                         (run_id, 'created', 'creation', timestamp, timestamp, encode(context), encode(limits), encode(files)))
        return run_id

    def get_run(self, run_id):
        with self.db.connect() as conn:
            return decode(conn.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone())

    def update_run(self, run_id, **fields):
        allowed = {'status', 'stage', 'context', 'limits', 'usage', 'elapsed', 'files', 'error', 'cancel_requested'}
        if not fields.keys() <= allowed:
            raise ValueError('Invalid run fields')
        fields['updated_at'] = now()
        fields = {k: encode(v) if k in {'context', 'limits', 'usage', 'files'} else v for k, v in fields.items()}
        with self.db.connect() as conn:
            conn.execute('UPDATE runs SET '+','.join(f'{k}=?' for k in fields)+' WHERE id=?', (*fields.values(), run_id))

    def claim(self, run_id, owner, lease_seconds=30):
        with self.db.connect() as conn:
            cursor = conn.execute('''UPDATE runs SET lease_owner=?, lease_until=?
                WHERE id=? AND (lease_owner IS NULL OR lease_until<?)
                AND NOT EXISTS (SELECT 1 FROM runs AS other WHERE other.id<>?
                    AND other.lease_owner IS NOT NULL AND other.lease_until>?
                    AND json_extract(other.files,'$.output_dir')=json_extract(runs.files,'$.output_dir') COLLATE NOCASE)''',
                                  (owner, time.time()+lease_seconds, run_id, time.time(), run_id, time.time()))
            if cursor.rowcount != 1:
                raise RuntimeError('Run is already owned by an active executor')

    def heartbeat(self, run_id, owner, lease_seconds=30):
        with self.db.connect() as conn:
            cursor = conn.execute('UPDATE runs SET lease_until=? WHERE id=? AND lease_owner=?', (time.time()+lease_seconds, run_id, owner))
            if cursor.rowcount != 1:
                raise RuntimeError('Run lease lost')

    def release(self, run_id, owner):
        with self.db.connect() as conn:
            conn.execute('UPDATE runs SET lease_owner=NULL,lease_until=0 WHERE id=? AND lease_owner=?', (run_id, owner))

    def create_pages(self, run_id, specs):
        timestamp = now()
        with self.db.connect() as conn:
            for position, spec in enumerate(specs):
                conn.execute('INSERT OR IGNORE INTO pages(id,run_id,position,spec,status,stage,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                             (uuid4().hex, run_id, position, encode(spec), 'pending', 'generation', timestamp, timestamp))
        return self.pages(run_id)

    def pages(self, run_id):
        with self.db.connect() as conn:
            return [decode(row) for row in conn.execute('SELECT * FROM pages WHERE run_id=? ORDER BY position', (run_id,))]

    def page(self, page_id):
        with self.db.connect() as conn:
            return decode(conn.execute('SELECT * FROM pages WHERE id=?', (page_id,)).fetchone())

    def mark_page(self, page_id, status, error=None):
        with self.db.connect() as conn:
            conn.execute('UPDATE pages SET status=?,error=?,updated_at=? WHERE id=?', (status, error, now(), page_id))

    def task(self, run_id, stage, page_id='', iteration=0):
        timestamp = now()
        with self.db.connect() as conn:
            conn.execute('INSERT OR IGNORE INTO tasks(id,run_id,page_id,stage,iteration,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                         (uuid4().hex, run_id, page_id, stage, iteration, 'pending', timestamp, timestamp))
            return decode(conn.execute('SELECT * FROM tasks WHERE run_id=? AND page_id=? AND stage=? AND iteration=?',
                                       (run_id, page_id, stage, iteration)).fetchone())

    def tasks(self, run_id):
        with self.db.connect() as conn:
            return [decode(row) for row in conn.execute('SELECT * FROM tasks WHERE run_id=? ORDER BY created_at,id', (run_id,))]

    def begin_task(self, task_id):
        with self.db.connect() as conn:
            conn.execute("UPDATE tasks SET status='running',attempts=attempts+1,error=NULL,updated_at=? WHERE id=?", (now(), task_id))

    def fail_task(self, task_id, status, error, retry=False):
        with self.db.connect() as conn:
            row = conn.execute('SELECT run_id,page_id FROM tasks WHERE id=?', (task_id,)).fetchone()
            conn.execute('UPDATE tasks SET status=?,error=?,retries=retries+?,updated_at=? WHERE id=?', (status,error,int(retry),now(),task_id))
            if retry:
                conn.execute('UPDATE runs SET retries=retries+1 WHERE id=?', (row['run_id'],))
                conn.execute('UPDATE pages SET retries=retries+1 WHERE id=?', (row['page_id'],))

    def complete_task(self, task_id, result, page_id=None, next_stage=None, iteration=0, files=None):
        """Commit task completion and page continuation point in one transaction."""
        with self.db.connect() as conn:
            conn.execute("UPDATE tasks SET status='completed',result=?,files=?,error=NULL,updated_at=? WHERE id=?",
                         (encode(result), encode(files or {}), now(), task_id))
            if page_id:
                old = decode(conn.execute('SELECT * FROM pages WHERE id=?', (page_id,)).fetchone())
                artifacts = dict(old['files']); artifacts.update(files or {})
                history = old['checkpoint'].get('history', [])
                history = (history + [{'stage': old['stage'], 'iteration': old['iteration'], 'files': files or {}}])[-2:]
                checkpoint = {'next_stage': next_stage, 'iteration': iteration, 'history': history, 'last_result': result}
                conn.execute('UPDATE pages SET status=?,stage=?,iteration=?,files=?,checkpoint=?,error=NULL,updated_at=? WHERE id=?',
                             ('completed' if next_stage == 'completion' else 'running', next_stage, iteration, encode(artifacts), encode(checkpoint), now(), page_id))

    def reset_page(self, page_id):
        with self.db.connect() as conn:
            conn.execute("UPDATE pages SET status='pending',stage='generation',iteration=0,checkpoint='{}',files='{}',error=NULL,updated_at=? WHERE id=?", (now(), page_id))
            conn.execute("UPDATE tasks SET status='pending' WHERE page_id=?", (page_id,))

    def interrupt_active(self, run_id, status, error):
        with self.db.connect() as conn:
            conn.execute("UPDATE tasks SET status='interrupted',error=?,updated_at=? WHERE run_id=? AND status='running'", (error,now(),run_id))
            conn.execute("UPDATE pages SET status=?,error=?,updated_at=? WHERE run_id=? AND status='running'", (status,error,now(),run_id))
