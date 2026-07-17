import os
import pathlib

def load_env(env_path=None):
    if not env_path:
        # Default to root directory .env
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

# Automatically load on import
load_env()

# Export centralized configurations
BIFROST_BASE_URL = os.environ.get("BIFROST_BASE_URL", "http://192.168.32.1:8888/v1")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "vertex/gemini-3.1-flash-lite")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "dummy_token")
SUPABASE_CONNECTION_STRING = os.environ.get("SUPABASE_CONNECTION_STRING", "")
BL_DB_PATH = os.environ.get("BL_DB_PATH", os.path.join(os.path.expanduser("~"), ".openclaw-backlink", "data", "backlink.db"))

def get_db_connection():
    if SUPABASE_CONNECTION_STRING:
        import psycopg2
        return psycopg2.connect(SUPABASE_CONNECTION_STRING)
    else:
        import sqlite3
        return sqlite3.connect(BL_DB_PATH)
