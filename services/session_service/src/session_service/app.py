from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Session Service")

_sessions: dict[str, dict] = {}

class SessionCreate(BaseModel):
    agent_id: str
    input: dict

@app.post("/tenants/{tenant}/sessions")
async def create_session(tenant: str, body: SessionCreate):
    sid = f"{tenant}:{body.agent_id}"
    _sessions[sid] = {"input": body.input}
    return {"session_id": sid}

@app.get("/tenants/{tenant}/sessions/{sid}")
async def get_session(tenant: str, sid: str):
    data = _sessions.get(sid)
    if not data:
        return {"error": "not found"}
    return {"session_id": sid, **data}

