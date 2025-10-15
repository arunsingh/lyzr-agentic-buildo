
from __future__ import annotations
from typing import List
from .events import Event

class AbstractEventStore:
    async def append(self, evt: Event) -> None: ...
    async def list(self, correlation_id: str) -> List[Event]: ...

class InMemoryStore(AbstractEventStore):
    def __init__(self):
        self._events: List[Event] = []

    async def append(self, evt: Event) -> None:
        if evt.idempotency_key and any(e.idempotency_key == evt.idempotency_key for e in self._events):
            return
        self._events.append(evt)

    async def list(self, correlation_id: str) -> List[Event]:
        return [e for e in self._events if e.correlation_id == correlation_id]
