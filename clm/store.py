"""Transactional SQLite state and file storage for a single Cloudera application."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .defaults import seed, migrate

class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'aurelia.sqlite3'
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, content BLOB NOT NULL)')
            conn.execute('BEGIN IMMEDIATE')
            if not conn.execute('SELECT 1 FROM state WHERE id=1').fetchone():
                old = self.directory / 'db.json'
                state = migrate(json.loads(old.read_text(encoding='utf-8-sig'))) if old.exists() else seed()
                for c in state['cases']:
                    for d in c['documents']:
                        if not d.get('sample'):
                            source = (self.directory / 'uploads' / d['id']).resolve()
                            if source.parent != (self.directory / 'uploads').resolve():
                                raise ValueError('Invalid legacy file identifier')
                            conn.execute('INSERT INTO files VALUES (?, ?)', (d['id'], source.read_bytes()))
                conn.execute('INSERT INTO state VALUES (1, ?)', (json.dumps(state),))
            conn.commit()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.execute('PRAGMA busy_timeout=30000')
        return conn

    @contextmanager
    def transaction(self, write=False):
        conn = self.connect()
        try:
            conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            db = json.loads(conn.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
            yield db, conn
            if write:
                db['revision'] += 1
                conn.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(db),))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
