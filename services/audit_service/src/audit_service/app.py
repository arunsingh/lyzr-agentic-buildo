from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Audit Service")

class DecisionRecordIn(BaseModel):
    correlation_id: str
    workflow_id: str
    node_id: str
    node_name: str
    node_kind: str
    allowed: bool
    policies_applied: list[str]
    input_snapshot: dict
    output_snapshot: dict
    model_info: dict
    tool_calls: list[dict]
    cost: dict
    latency_ms: float | None = None

_records: list[DecisionRecordIn] = []

@app.post("/decisions")
async def ingest(record: DecisionRecordIn):
    _records.append(record)
    return {"ok": True}

@app.get("/decisions")
async def list_records():
    return {"count": len(_records), "items": [r.dict() for r in _records]}

