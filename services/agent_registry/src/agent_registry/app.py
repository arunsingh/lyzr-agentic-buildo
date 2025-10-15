from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agentic_core.types import AgentSpec

app = FastAPI(title="Agent Registry")

_registry: dict[str, AgentSpec] = {}

class PutAgentReq(BaseModel):
    spec: AgentSpec

@app.post("/tenants/{tenant}/agents")
async def create_agent(tenant: str, req: PutAgentReq):
    spec = req.spec
    key = f"{tenant}:{spec.id}:{spec.version}"
    if key in _registry:
        raise HTTPException(409, "version exists")
    _registry[key] = spec
    return {"id": spec.id, "version": spec.version, "owner": spec.owner}

@app.get("/tenants/{tenant}/agents/{agent_id}/versions/{version}")
async def get_agent(tenant: str, agent_id: str, version: str):
    key = f"{tenant}:{agent_id}:{version}"
    spec = _registry.get(key)
    if not spec:
        raise HTTPException(404, "not found")
    return spec

