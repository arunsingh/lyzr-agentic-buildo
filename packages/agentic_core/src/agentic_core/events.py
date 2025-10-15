
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import time, uuid

@dataclass(frozen=True)
class Event:
    type: str
    payload: Dict[str, Any]
    ts: float
    id: str
    correlation_id: str
    causation_id: Optional[str] = None
    idempotency_key: Optional[str] = None

    @staticmethod
    def new(type: str, payload: Dict[str, Any], *,
            correlation_id: Optional[str] = None,
            causation_id: Optional[str] = None,
            idempotency_key: Optional[str] = None) -> "Event":
        return Event(
            type=type,
            payload=payload,
            ts=time.time(),
            id=str(uuid.uuid4()),
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id,
            idempotency_key=idempotency_key,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
