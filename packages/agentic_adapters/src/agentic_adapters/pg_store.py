
from __future__ import annotations
import json
from typing import List, Tuple
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
CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY,
  correlation_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  delivered BOOLEAN DEFAULT FALSE,
  ts DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
  snapshot_id TEXT PRIMARY KEY,
  correlation_id TEXT NOT NULL,
  items JSONB NOT NULL,
  ts DOUBLE PRECISION NOT NULL
);
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

    async def append_with_outbox(self, evt: Event) -> Tuple[bool, Event]:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            async with c.transaction():
                try:
                    await c.execute(
                        """INSERT INTO events(id,type,ts,correlation_id,causation_id,idempotency_key,payload)
                               VALUES($1,$2,$3,$4,$5,$6,$7)""",
                        evt.id, evt.type, evt.ts, evt.correlation_id, evt.causation_id, evt.idempotency_key, json.dumps(evt.payload)
                    )
                except asyncpg.UniqueViolationError:
                    return False, evt
                await c.execute(
                    """INSERT INTO outbox(id,correlation_id,payload,delivered,ts)
                           VALUES($1,$2,$3,FALSE,$4)""",
                    evt.id, evt.correlation_id, json.dumps(evt.to_dict()), evt.ts
                )
        return True, evt

    async def snapshot(self, correlation_id: str) -> str:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT id,type,ts,correlation_id,causation_id,idempotency_key,payload FROM events WHERE correlation_id=$1 ORDER BY ts ASC", correlation_id)
            items = [Event(id=r[0], type=r[1], ts=r[2], correlation_id=r[3], causation_id=r[4], idempotency_key=r[5], payload=r[6]).to_dict() for r in rows]
            snapshot_id = f"{correlation_id}:{len(items)}"
            await c.execute("""INSERT INTO snapshots(snapshot_id,correlation_id,items,ts) VALUES($1,$2,$3,extract(epoch from now()))""", snapshot_id, correlation_id, json.dumps(items))
            return snapshot_id

    async def list_snapshots(self, correlation_id: str) -> List[str]:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT snapshot_id FROM snapshots WHERE correlation_id=$1 ORDER BY ts ASC", correlation_id)
            return [r[0] for r in rows]

    async def load_snapshot(self, correlation_id: str, snapshot_id: str) -> List[Event]:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            row = await c.fetchrow("SELECT items FROM snapshots WHERE snapshot_id=$1", snapshot_id)
            if not row:
                return []
            items = json.loads(row[0])
        return [Event(**e) for e in items]

    async def fetch_outbox(self, limit: int = 100) -> List[Event]:
        pool = await self._pool_get()
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT id,payload FROM outbox WHERE delivered=FALSE ORDER BY ts ASC LIMIT $1", limit)
        return [Event(**json.loads(r[1])) for r in rows]

    async def mark_outbox_delivered(self, ids: List[str]) -> None:
        if not ids:
            return
        pool = await self._pool_get()
        async with pool.acquire() as c:
            await c.execute("UPDATE outbox SET delivered=TRUE WHERE id = ANY($1::text[])", ids)
