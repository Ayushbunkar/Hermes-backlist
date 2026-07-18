import os
import pathlib
import sys

def load_env(env_path=None):
    if not env_path:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
        env_path = os.path.join(root_dir, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = val

load_env()

BIFROST_BASE_URL = os.environ.get("BIFROST_BASE_URL", "")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "vertex/gemini-3.1-flash-lite")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SUPABASE_CONNECTION_STRING = os.environ.get("SUPABASE_CONNECTION_STRING", "")
BL_DB_PATH = os.environ.get("BL_DB_PATH", os.path.join(os.path.expanduser("~"), ".openclaw-backlink", "data", "backlink.db"))

class PostgresSQLiteAdapter:
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None

    def _translate_sql(self, sql):
        sql = sql.replace("datetime('now')", "timezone('utc', now())")
        sql = sql.replace("INSERT OR REPLACE", "INSERT INTO")
        sql = sql.replace('?', '%s')
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("PRAGMA journal_mode=WAL", "SELECT 1")
        sql = sql.replace("PRAGMA foreign_keys=ON", "SELECT 1")
        return sql

    def execute(self, sql, parameters=()):
        import psycopg2.extras
        c = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute(self._translate_sql(sql), parameters)
        return c

    def executemany(self, sql, parameters_seq):
        import psycopg2.extras
        c = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.executemany(self._translate_sql(sql), parameters_seq)
        return c

    def executescript(self, sql):
        c = self._conn.cursor()
        c.execute(self._translate_sql(sql))
        return c

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

def get_db_connection():
    if SUPABASE_CONNECTION_STRING:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(SUPABASE_CONNECTION_STRING)
        return PostgresSQLiteAdapter(conn)
    else:
        import sqlite3
        return sqlite3.connect(BL_DB_PATH)

if SUPABASE_CONNECTION_STRING:
    class MockSQLite3:
        class OperationalError(Exception): pass
        class IntegrityError(Exception): pass
        class Error(Exception): pass
        Row = "Row"
        Connection = "Connection"
    sys.modules['sqlite3'] = MockSQLite3()
