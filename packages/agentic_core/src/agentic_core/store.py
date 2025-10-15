
from __future__ import annotations
from typing import List, Tuple
from .events import Event

class AbstractEventStore:
    async def append(self, evt: Event) -> None: ...
    async def list(self, correlation_id: str) -> List[Event]: ...
    async def append_with_outbox(self, evt: Event) -> Tuple[bool, Event]: ...
    async def snapshot(self, correlation_id: str) -> str: ...
    async def list_snapshots(self, correlation_id: str) -> List[str]: ...
    async def load_snapshot(self, correlation_id: str, snapshot_id: str) -> List[Event]: ...
    async def fetch_outbox(self, limit: int = 100) -> List[Event]: ...
    async def mark_outbox_delivered(self, ids: List[str]) -> None: ...

class InMemoryStore(AbstractEventStore):
    def __init__(self):
        self._events: List[Event] = []
        self._snapshots: dict[str, List[Event]] = {}
        self._outbox: List[Event] = []

    async def append(self, evt: Event) -> None:
        if evt.idempotency_key and any(e.idempotency_key == evt.idempotency_key for e in self._events):
            return
        self._events.append(evt)

    async def append_with_outbox(self, evt: Event) -> Tuple[bool, Event]:
        # In-memory transactional outbox simulation: check idempotency then append
        already = evt.idempotency_key and any(e.idempotency_key == evt.idempotency_key for e in self._events)
        if already:
            return False, evt
        self._events.append(evt)
        self._outbox.append(evt)
        return True, evt

    async def list(self, correlation_id: str) -> List[Event]:
        return [e for e in self._events if e.correlation_id == correlation_id]

    async def snapshot(self, correlation_id: str) -> str:
        items = await self.list(correlation_id)
        snap_id = f"{correlation_id}:{len(items)}"
        self._snapshots[snap_id] = list(items)
        return snap_id

    async def list_snapshots(self, correlation_id: str) -> List[str]:
        prefix = f"{correlation_id}:"
        return [k for k in self._snapshots.keys() if k.startswith(prefix)]

    async def load_snapshot(self, correlation_id: str, snapshot_id: str) -> List[Event]:
        return list(self._snapshots.get(snapshot_id, []))

    async def fetch_outbox(self, limit: int = 100) -> List[Event]:
        return list(self._outbox[:limit])

    async def mark_outbox_delivered(self, ids: List[str]) -> None:
        self._outbox = [e for e in self._outbox if e.id not in ids]
