# app.py — Treehole Web 界面 (FastAPI + 纯前端)
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from cli.main import (
    create_agent,
    generate_greeting,
    load_persona_text,
    local_persona_path,
    persona_setup_needed,
    save_local_persona,
)
from core.config import AppConfig

# ============ 初始化 ============

config = AppConfig.from_file()
app = FastAPI(title="Treehole")

agent = None
emotion = None

SETTINGS_PATH = Path(config.memory.data_dir) / "settings.json"


def _load_settings_from_file() -> dict | None:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _try_init_agent() -> bool:
    """Try to create agent from env vars or saved settings. Returns True on success."""
    global agent, emotion
    load_dotenv()
    has_env = bool(os.environ.get("OPENAI_API_KEY"))

    if has_env:
        try:
            agent, emotion = create_agent(config)
            return True
        except Exception:
            return False

    saved = _load_settings_from_file()
    if saved and saved.get("api_key"):
        os.environ.setdefault("OPENAI_BASE_URL", saved.get("base_url", "https://api.openai.com/v1"))
        os.environ.setdefault("OPENAI_API_KEY", saved["api_key"])
        os.environ.setdefault("OPENAI_MODEL", saved.get("model", "gpt-4.1-mini"))
        try:
            agent, emotion = create_agent(config)
            return True
        except Exception:
            return False

    return False


_try_init_agent()

# ============ 前端 HTML ============

HTML_PAGE = Path(__file__).parent / "web" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE.read_text(encoding="utf-8")


# ============ API ============


@app.get("/api/settings")
async def get_settings():
    return {"configured": agent is not None}


@app.post("/api/settings")
async def save_settings(req: Request):
    global agent, emotion
    body = await req.json()
    base_url = body.get("base_url", "").strip()
    api_key = body.get("api_key", "").strip()
    model = body.get("model", "").strip()

    if not api_key:
        return {"ok": False, "error": "API key is required"}

    os.environ["OPENAI_BASE_URL"] = base_url or "https://api.openai.com/v1"
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_MODEL"] = model or "gpt-4.1-mini"

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps({
        "base_url": os.environ["OPENAI_BASE_URL"],
        "api_key": api_key,
        "model": os.environ["OPENAI_MODEL"],
    }, ensure_ascii=False), encoding="utf-8")

    try:
        agent, emotion = create_agent(config)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/greeting")
async def greeting():
    if agent is None:
        return {"text": "你好呀，今天想聊点什么？", "absent": False}
    text = generate_greeting(agent.llm, agent.profile, agent.memory)
    parts = []
    if text:
        parts.append(text)
    if emotion.bond.check_return_after_absence():
        parts.append("好久不见！")
    absent = emotion.bond.check_return_after_absence() if emotion else False
    return {"text": "\n\n".join(parts) if parts else "你好呀，今天想聊点什么？", "absent": absent}


@app.post("/api/chat")
async def chat(req: Request):
    if agent is None:
        return {"error": "not configured"}

    body = await req.json()
    message = body.get("message", "")

    def stream():
        for token in agent.run_stream(message):
            yield {"data": json.dumps({"token": token}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@app.get("/api/memories")
async def memories():
    if agent is None:
        return {"entries": [], "count": 0}
    entries = agent.memory.list_memories()
    return {"entries": entries, "count": len(entries)}


@app.post("/api/memories/add")
async def add_memory(req: Request):
    if agent is None:
        return {"ok": False, "error": "not configured"}
    body = await req.json()
    content = body.get("content", "").strip()
    if content:
        agent.memory.save_memory(content, category="手动", resolved=True)
    return {"ok": True}


@app.post("/api/memories/delete")
async def delete_memory(req: Request):
    if agent is None:
        return {"ok": False, "error": "not configured"}
    body = await req.json()
    idx = body.get("index")
    try:
        agent.memory.delete_memory(idx)
        return {"ok": True}
    except (ValueError, IndexError) as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/profile")
async def profile():
    if agent is None:
        return {"text": ""}
    return {"text": agent.profile.load() or ""}


@app.get("/api/persona")
async def persona():
    return {
        "text": load_persona_text(config),
        "needs_setup": persona_setup_needed(config),
        "path": str(local_persona_path(config)),
    }


@app.post("/api/persona")
async def save_persona(req: Request):
    if agent is None:
        return {"ok": False, "error": "not configured"}
    body = await req.json()
    text = body.get("text", "").strip()
    if not text:
        return {"ok": False, "error": "persona text is empty"}

    path = save_local_persona(config, text)
    agent.context_manager.persona = text
    return {"ok": True, "path": str(path)}


@app.get("/api/emotion")
async def emotion_state():
    if not emotion:
        return {"enabled": False}
    state = emotion.get_state()
    return {
        "enabled": True,
        "mood_value": state.mood_value,
        "mood_label": state.mood_label,
        "mood_hearts": state.mood_hearts,
        "bond_level": state.bond_level,
        "bond_name": state.bond_name,
        "energy": state.energy,
    }


@app.post("/api/reset")
async def reset():
    if agent is None:
        return {"ok": False, "error": "not configured"}
    agent.memory.clear()
    return {"ok": True}


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
