from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx, os

app = FastAPI(title="Tool Gateway (MCP proxy)")

class ToolCall(BaseModel):
    server: str
    tool: str
    args: dict

@app.post("/call")
async def call_tool(req: ToolCall):
    # OPA gate
    opa_url = os.getenv("AOB_OPA_URL", "http://opa:8181")
    input_doc = {
        "server": req.server,
        "tool": req.tool,
        "args": req.args,
        "policies": ["tool_allowlist"],
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{opa_url}/v1/data/aob/allow", json={"input": input_doc})
            r.raise_for_status()
            res = r.json().get("result")
            allowed = res.get("allow", res) if isinstance(res, dict) else bool(res)
            if not allowed:
                raise HTTPException(403, "tool call denied by policy")
    except Exception as e:
        raise HTTPException(502, f"policy evaluation error: {e}")

    # Proxy (demo): just echo, real MCP proxying would connect to server
    return {"server": req.server, "tool": req.tool, "result": {"ok": True}}

