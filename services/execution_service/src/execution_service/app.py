from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Execution Service")

class EnqueueReq(BaseModel):
    agent_id: str
    session_id: str | None = None
    input: dict

@app.post("/invocations")
async def enqueue(req: EnqueueReq):
    # Placeholder: In production, enqueue to Kafka and schedule a runner pod/microVM
    return {"status": "queued", "agent_id": req.agent_id, "session_id": req.session_id}

