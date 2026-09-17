"""Durable PostgreSQL store for serverless deployments; same atomic API as SQLite."""
from contextlib import contextmanager
import re
import threading
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from .defaults import seed

class PostgresStore:
    def __init__(self,url,schema='bankclm'):
        if not re.fullmatch(r'bankclm(?:_[a-z0-9_]+)?',schema): raise ValueError('Invalid storage namespace')
        self.url=url
        self.schema=schema
        self._ready=False
        self._lock=threading.Lock()

    def table(self,name):
        return sql.Identifier(self.schema,name)

    def connect(self):
        conn=psycopg.connect(self.url,connect_timeout=15)
        conn.execute('SET LOCAL statement_timeout = 20000')
        return conn

    def initialize(self):
        if self._ready: return
        with self._lock:
            if self._ready: return
            with self.connect() as conn:
                # Serialize first cold starts, including DDL and seed insertion.
                conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(self.schema,))
                conn.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(self.schema)))
                conn.execute(sql.SQL('CREATE TABLE IF NOT EXISTS {} (id integer PRIMARY KEY CHECK(id=1),body jsonb NOT NULL)').format(self.table('state')))
                conn.execute(sql.SQL('CREATE TABLE IF NOT EXISTS {} (id text PRIMARY KEY,content bytea NOT NULL)').format(self.table('files')))
                conn.execute(sql.SQL('INSERT INTO {} VALUES (1,%s) ON CONFLICT(id) DO NOTHING').format(self.table('state')),(Jsonb(seed()),))
            self._ready=True

    @contextmanager
    def transaction(self,write=False):
        self.initialize()
        with self.connect() as conn:
            query=sql.SQL('SELECT body FROM {} WHERE id=1'+(' FOR UPDATE' if write else '')).format(self.table('state'))
            db=conn.execute(query).fetchone()[0]
            yield db,conn
            if write:
                db['revision']+=1
                conn.execute(sql.SQL('UPDATE {} SET body=%s WHERE id=1').format(self.table('state')),(Jsonb(db),))

    def put_file(self,conn,uid,content):
        conn.execute(sql.SQL('INSERT INTO {} VALUES (%s,%s)').format(self.table('files')),(uid,content))

    def get_file(self,conn,uid):
        row=conn.execute(sql.SQL('SELECT content FROM {} WHERE id=%s').format(self.table('files')),(uid,)).fetchone()
        return bytes(row[0]) if row else None
