"""Privacy-by-default structured metadata; prompts, responses and arguments are never logged."""
import json
import os
from pathlib import Path
import re
from threading import RLock
import traceback
from .context import CURRENT_EXECUTION
from .state import now


def safe_error(exc):
    # Exception messages may embed a provider key, request body, or user profile.
    return type(exc).__name__


class Tracer:
    FIELDS = {'task_id', 'page_id', 'stage', 'agent', 'status', 'model', 'tool', 'request_id',
              'prompt_tokens', 'completion_tokens', 'cost', 'cost_source', 'duration_ms',
              'retry', 'error', 'message_count', 'image_count', 'parameter_names', 'reason',
              'iteration', 'pending_requests'}

    def __init__(self, database, runs_dir):
        self.db = database
        self.runs_dir = Path(runs_dir)
        self._lock = RLock()

    def emit(self, run_id, event, **fields):
        scope = CURRENT_EXECUTION.get()
        data = {}
        if scope and scope.run_id == run_id:
            data.update(task_id=scope.task_id, page_id=scope.page_id, stage=scope.stage, agent=scope.agent)
        data.update({k: v for k, v in fields.items() if k in self.FIELDS})
        timestamp = now()
        payload = json.dumps(data, ensure_ascii=False)
        with self._lock:
            with self.db.connect() as conn:
                cursor = conn.execute('INSERT INTO traces(run_id,timestamp,event,data) VALUES(?,?,?,?)', (run_id,timestamp,event,payload))
                record = {'id': cursor.lastrowid, 'run_id': run_id, 'timestamp': timestamp, 'event': event, **data}
            path = self.runs_dir / run_id / 'trace.jsonl'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False)+'\n')
        return record

    def query(self, run_id, after_id=0):
        with self.db.connect() as conn:
            return [{'id': row['id'], 'run_id': run_id, 'timestamp': row['timestamp'], 'event': row['event'], **json.loads(row['data'])}
                    for row in conn.execute('SELECT * FROM traces WHERE run_id=? AND id>? ORDER BY id', (run_id,after_id))]

    def diagnostic_path(self, run_id):
        return self.runs_dir / run_id / 'diagnostics.jsonl'

    def exception(self, run_id, exc, **fields):
        """Local developer traceback, separate from public/MCP trace and without locals."""
        from resumeagent.config import config
        secrets = [str(value) for key, value in {**config, **os.environ}.items()
                   if value and len(str(value)) >= 4 and
                   any(part in key.upper() for part in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD'))]
        record = self.db
        # Profiles and feedback can appear in SDK exceptions; redact exact saved values too.
        with record.connect() as conn:
            row = conn.execute('SELECT context FROM runs WHERE id=?', (run_id,)).fetchone()
        if row:
            context = json.loads(row['context'])
            secrets += [v for v in context.get('profile', {}).values() if isinstance(v, str) and len(v) >= 4]
            if context.get('feedback'):
                secrets.append(context['feedback'])
        def redact(value):
            for secret in sorted(set(secrets), key=len, reverse=True):
                value = value.replace(secret, '[REDACTED]')
            value = re.sub(r'(?i)(Bearer\s+)[^\s\"\']+', r'\1[REDACTED]', value)
            return re.sub(r'\bsk-[A-Za-z0-9_-]+', '[REDACTED]', value)
        scope = CURRENT_EXECUTION.get()
        detail = {'run_id': run_id, 'timestamp': now(), 'error_type': safe_error(exc),
                  'message': redact(str(exc)),
                  'traceback': redact(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)))}
        if scope and scope.run_id == run_id:
            detail.update(task_id=scope.task_id, page_id=scope.page_id, stage=scope.stage, agent=scope.agent)
        detail.update({k:v for k,v in fields.items() if k in self.FIELDS})
        path = self.diagnostic_path(run_id)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(detail, ensure_ascii=False)+'\n')
        return path
