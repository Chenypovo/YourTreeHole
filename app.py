# app.py — Treehole Web 界面 (FastAPI + 纯前端)
from __future__ import annotations

import json
from pathlib import Path

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
agent, emotion = create_agent(config)

app = FastAPI(title="Treehole")

# ============ 前端 HTML ============

HTML_PAGE = Path(__file__).parent / "web" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE.read_text(encoding="utf-8")


# ============ API ============


@app.get("/api/greeting")
async def greeting():
    text = generate_greeting(agent.llm, agent.profile, agent.memory)
    parts = []
    if text:
        parts.append(text)
    if emotion.bond.check_return_after_absence():
        parts.append("好久不见！")
    absent = emotion.bond.check_return_after_absence()
    return {"text": "\n\n".join(parts) if parts else "你好呀，今天想聊点什么？", "absent": absent}


@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")

    def stream():
        for token in agent.run_stream(message):
            yield {"data": json.dumps({"token": token}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@app.get("/api/memories")
async def memories():
    entries = agent.memory.list_memories()
    return {"entries": entries, "count": len(entries)}


@app.post("/api/memories/add")
async def add_memory(req: Request):
    body = await req.json()
    content = body.get("content", "").strip()
    if content:
        agent.memory.save_memory(content, category="手动", resolved=True)
    return {"ok": True}


@app.post("/api/memories/delete")
async def delete_memory(req: Request):
    body = await req.json()
    idx = body.get("index")
    try:
        agent.memory.delete_memory(idx)
        return {"ok": True}
    except (ValueError, IndexError) as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/profile")
async def profile():
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
    agent.memory.clear()
    return {"ok": True}


# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
