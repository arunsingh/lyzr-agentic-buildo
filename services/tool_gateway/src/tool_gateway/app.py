from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Tool Gateway (MCP proxy)")

class ToolCall(BaseModel):
    server: str
    tool: str
    args: dict

@app.post("/call")
async def call_tool(req: ToolCall):
    # Placeholder: proxy to MCP server with OPA guard and redaction
    return {"server": req.server, "tool": req.tool, "result": {"ok": True}}

