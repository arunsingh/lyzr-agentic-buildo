from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AgentSpec(BaseModel):
    id: str
    version: str
    owner: str
    graph: Dict[str, Any] | None = None
    tools: List[Dict[str, Any]] | None = None
    policies: List[str] | None = None
    model_profile: Dict[str, Any] | None = None
    memory: Dict[str, Any] | None = None


@dataclass(frozen=True)
class DecisionRecord:
    correlation_id: str
    workflow_id: str
    node_id: str
    node_name: str
    node_kind: str
    allowed: bool
    policies_applied: List[str]
    input_snapshot: Dict[str, Any]
    output_snapshot: Dict[str, Any]
    model_info: Dict[str, Any]
    tool_calls: List[Dict[str, Any]]
    cost: Dict[str, Any]
    latency_ms: Optional[float]
    # extended fields for deterministic replay/debug
    prompt: Optional[str] = None
    model_version: Optional[str] = None
    tool_io: Optional[List[Dict[str, Any]]] = None
    feature_flags: Optional[Dict[str, Any]] = None

