from __future__ import annotations
import asyncio
import json
from typing import Optional
from .types import DecisionRecord

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


class HttpAuditSink:
    def __init__(self, endpoint: str = "http://localhost:8085/decisions"):
        self.endpoint = endpoint

    def emit(self, record: DecisionRecord) -> None:
        if httpx is None:
            return
        asyncio.create_task(self._post(record))

    async def _post(self, record: DecisionRecord) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(self.endpoint, json={
                "correlation_id": record.correlation_id,
                "workflow_id": record.workflow_id,
                "node_id": record.node_id,
                "node_name": record.node_name,
                "node_kind": record.node_kind,
                "allowed": record.allowed,
                "policies_applied": record.policies_applied,
                "input_snapshot": record.input_snapshot,
                "output_snapshot": record.output_snapshot,
                "model_info": record.model_info,
                "tool_calls": record.tool_calls,
                "cost": record.cost,
                "latency_ms": record.latency_ms,
            })

