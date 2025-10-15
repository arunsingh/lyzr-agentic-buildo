
from __future__ import annotations
import json
from typing import List
import asyncpg
from agentic_core.store import AbstractEventStore
from agentic_core.events import Event

DDL = """CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  ts DOUBLE PRECISION NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT,
  idempotency_key TEXT,
  payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_corr ON events(correlation_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_idem ON events(idempotency_key) WHERE idempotency_key IS NOT NULL;
"""

class PostgresEventStore(AbstractEventStore):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def _pool_get(self) -> asyncpg.Pool:
        if not self._pool:
            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
            async with self._pool.acquire() as c:
                await c.execute(DDL)
        return self._pool

    async def append(self, evt: Event) -> None:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            try:
                await c.execute(
                    """INSERT INTO events(id,type,ts,correlation_id,causation_id,idempotency_key,payload)
                           VALUES($1,$2,$3,$4,$5,$6,$7)""",
                    evt.id, evt.type, evt.ts, evt.correlation_id, evt.causation_id, evt.idempotency_key, json.dumps(evt.payload)
                )
            except asyncpg.UniqueViolationError:
                # idempotency hit
                pass

    async def list(self, correlation_id: str) -> List[Event]:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT id,type,ts,correlation_id,causation_id,idempotency_key,payload FROM events WHERE correlation_id=$1 ORDER BY ts ASC", correlation_id)
        return [Event(id=r[0], type=r[1], ts=r[2], correlation_id=r[3], causation_id=r[4], idempotency_key=r[5], payload=r[6]) for r in rows]
