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

BIFROST_BASE_URL = os.environ.get("BIFROST_BASE_URL", "https://placing-reliability-container-oecd.trycloudflare.com/v1")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "ollama/qwen3-coder-next:latest")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SUPABASE_CONNECTION_STRING = os.environ.get("SUPABASE_CONNECTION_STRING", "")
BL_DB_PATH = os.environ.get("BL_DB_PATH", os.path.join(os.path.expanduser("~"), ".openclaw-backlink", "data", "backlink.db"))

class PostgresSQLiteAdapter:
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None

    def _translate_sql(self, sql):
        import re
        if sql.startswith("PRAGMA table_info("):
            match = re.search(r"PRAGMA table_info\((.+?)\)", sql)
            if match:
                table_name = match.group(1).strip("'\"")
                return f"SELECT column_name AS name FROM information_schema.columns WHERE table_name = '{table_name}'"

        sql = re.sub(r"datetime\('now',\s*\?\s*\|\|\s*'([^']+)'\)", r"NOW() AT TIME ZONE 'UTC' + CAST(? || ' \1' AS INTERVAL)", sql)
        sql = re.sub(r"datetime\('now',\s*\?\)", r"NOW() AT TIME ZONE 'UTC' + CAST(? AS INTERVAL)", sql)
        sql = re.sub(r"datetime\('now',\s*'([^']+)'\)", r"NOW() AT TIME ZONE 'UTC' + INTERVAL '\1'", sql)
        sql = sql.replace("datetime('now')", "timezone('utc', now())")
        
        is_ignore = "INSERT OR IGNORE" in sql
        sql = sql.replace("INSERT OR IGNORE", "INSERT INTO")
        sql = sql.replace("INSERT OR REPLACE", "INSERT INTO")
        sql = sql.replace('?', '%s')
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("PRAGMA journal_mode=WAL", "SELECT 1")
        sql = sql.replace("PRAGMA foreign_keys=ON", "SELECT 1")
        if is_ignore and "ON CONFLICT" not in sql:
            sql += " ON CONFLICT DO NOTHING"
        return sql

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def cursor(self):
        import psycopg2.extras
        return self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def execute(self, sql, parameters=()):
        import psycopg2.extras
        c = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute(self._translate_sql(sql), parameters)
        return c

    def executemany(self, sql, parameters_seq):
        import psycopg2.extras
        c = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.executemany(self._translate_sql(sql), parameters_seq)
        return c

    def executescript(self, sql):
        c = self._conn.cursor()
        c.execute(self._translate_sql(sql))
        return c

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

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
