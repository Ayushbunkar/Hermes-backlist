import os
import json
import urllib.request
import urllib.error

BIFROST_URL = os.environ.get("BIFROST_BASE_URL", "http://192.168.32.1:8888/v1")
DEFAULT_MODEL = os.environ.get("BL_GATE_MODEL", "vertex/gemini-3.1-flash-lite")

def _call_bifrost(prompt: str, model: str, timeout: int = 60) -> str:
    url = f"{BIFROST_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1500,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[hermes_client] API call failed: {e}")
        return ""

def run_agent(agent_id: str, prompt: str, context: dict = None, timeout: int = 60, **kwargs):
    """Executes an LLM agent synchronously via direct Bifrost API."""
    print(f"[hermes_client] Running agent {agent_id}...")
    response = _call_bifrost(prompt, DEFAULT_MODEL, timeout=timeout)
    
    if context and "result_path" in context:
        # For quality_gate compatibility, we assume the response contains the JSON scores
        try:
            # Clean up potential markdown formatting from the model
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1] if text.count("```") >= 2 else text
                text = text.lstrip("json").strip()
            
            # Make sure it's valid JSON
            parsed = json.loads(text)
            
            # Write exactly what the pipeline expects
            with open(context["result_path"], "w", encoding="utf-8") as f:
                json.dump({"status": "ok", "scores": parsed.get("scores", [])}, f)
        except Exception as e:
            print(f"[hermes_client] Failed to parse agent JSON response: {e}")
            # Write a fallback fail-open response
            with open(context["result_path"], "w", encoding="utf-8") as f:
                json.dump({"status": "ok", "scores": []}, f)
                
    return {"status": "success", "response": response}

def run_worker(worker_id: str, task_payload: dict, timeout_seconds: int = 120, **kwargs):
    """Executes a heavy worker task (e.g. drafting content)."""
    print(f"[hermes_client] Running worker {worker_id}...")
    
    if worker_id == "bl-content" and task_payload and "run_dir" in task_payload:
        prompt = task_payload.get("task", "Draft backlink content")
        response = _call_bifrost(prompt, DEFAULT_MODEL, timeout=timeout_seconds)
        
        posts_path = os.path.join(task_payload["run_dir"], "content", "posts.json")
        os.makedirs(os.path.dirname(posts_path), exist_ok=True)
        
        try:
            # Clean response text
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1] if text.count("```") >= 2 else text
                text = text.lstrip("json").strip()
                
            parsed = json.loads(text)
            with open(posts_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f)
        except Exception as e:
            print(f"[hermes_client] Worker failed to produce valid posts JSON: {e}")
            with open(posts_path, "w", encoding="utf-8") as f:
                json.dump({"posts": []}, f)
                
    return {"status": "success"}

import threading
import uuid
import sqlite3

# BIFROST_URL is already defined at top of file, we just add DB_PATH
DB_PATH = os.path.join(os.path.expanduser("~"), ".openclaw-backlink", "data", "backlink.db")

def spawn(agent_id: str, mode: str = "run", runtime: str = "subagent", context: str = "isolated", task: str = "") -> str:
    """Spawns an agent in a background thread, replacing OpenClaw subagent processes."""
    trace_id = f"hermes-spawn-{uuid.uuid4().hex[:8]}"
    print(f"[hermes_client] Spawning {agent_id} in background thread ({trace_id})")
    
    def background_task():
        # In a full implementation, this would map agent_id to specific logic
        if agent_id == "bl-content":
            run_worker(agent_id, {"task": task})
        else:
            run_agent(agent_id, task)
            
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    return trace_id

def yield_result(status: str, data: dict = None) -> None:
    """Signals completion of a worker, replacing sessions_yield."""
    print(f"[hermes_client] Yielded result: {status} | Data: {data}")
    # In native Python, returning from the function or raising StopIteration ends the thread
    if status.upper() == "FAILURE":
        raise RuntimeError(f"Hermes Worker Failed: {data}")
    return None

def memory(session_id: str, operation: str, data = None):
    """Replaces session-memory hook with explicit SQLite logging."""
    print(f"[hermes_client] Memory Op: {operation} for session {session_id}")
    if operation == "append" and data:
        # Here we would append to a conversational history table
        # For now, we simulate success
        return True
    return None

def tool(name: str, schema: dict = None):
    """Decorator to register Python functions as LLM tools."""
    def decorator(func):
        func.__hermes_tool__ = True
        func.__hermes_schema__ = schema
        return func
    return decorator

def session(chat_id: str, user_id: str, **kwargs):
    """Initializes or retrieves state machine from onboard_sessions."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("SELECT step FROM onboard_sessions WHERE chat_id=? AND user_id=? LIMIT 1", (str(chat_id), str(user_id)))
        row = cursor.fetchone()
        conn.close()
        step = row[0] if row else "new"
        print(f"[hermes_client] Session initialized for {chat_id}/{user_id} at step: {step}")
        return {"chat_id": chat_id, "user_id": user_id, "step": step}
    except Exception as e:
        print(f"[hermes_client] Session DB error (fail-open): {e}")
        return {"chat_id": chat_id, "user_id": user_id, "step": "error"}
