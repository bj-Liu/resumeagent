"""SQLite connection/transaction ownership; no workflow decisions live here."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3


class Database:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, stage TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                retries INTEGER NOT NULL DEFAULT 0, files TEXT NOT NULL DEFAULT '{}',
                error TEXT, context TEXT NOT NULL, limits TEXT NOT NULL,
                usage TEXT NOT NULL DEFAULT '{}', elapsed REAL NOT NULL DEFAULT 0,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                lease_owner TEXT, lease_until REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                position INTEGER NOT NULL, spec TEXT NOT NULL, status TEXT NOT NULL,
                stage TEXT NOT NULL, iteration INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                retries INTEGER NOT NULL DEFAULT 0, files TEXT NOT NULL DEFAULT '{}',
                error TEXT, checkpoint TEXT NOT NULL DEFAULT '{}',
                UNIQUE(run_id, position)
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                page_id TEXT NOT NULL DEFAULT '', stage TEXT NOT NULL,
                iteration INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                retries INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
                files TEXT NOT NULL DEFAULT '{}', error TEXT,
                result TEXT NOT NULL DEFAULT '{}',
                UNIQUE(run_id, page_id, stage, iteration)
            );
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
                timestamp TEXT NOT NULL, event TEXT NOT NULL, data TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS traces_run ON traces(run_id, id);
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
                request_id TEXT NOT NULL, model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL, completion_tokens INTEGER NOT NULL,
                cost REAL NOT NULL, timestamp TEXT NOT NULL
            );
            ''')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=30000')
        try:
            with conn:
                yield conn
        finally:
            conn.close()
