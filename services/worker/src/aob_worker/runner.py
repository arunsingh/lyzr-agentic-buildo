
from __future__ import annotations
import asyncio, os, random, sys
from typing import Optional

from agentic_core.bus import AbstractEventBus
from agentic_core.events import Event
from agentic_core.store import AbstractEventStore

try:
    from agentic_adapters.pg_store import PostgresEventStore
except Exception:
    PostgresEventStore = None  # type: ignore

try:
    from agentic_adapters.kafka_bus import KafkaBus
except Exception:
    KafkaBus = None  # type: ignore


async def build_store() -> Optional[AbstractEventStore]:
    dsn = os.getenv("AOB_POSTGRES_DSN")
    if not dsn or PostgresEventStore is None:
        print("[worker] No Postgres DSN; outbox worker disabled.", file=sys.stderr)
        return None
    return PostgresEventStore(dsn)


async def build_bus() -> Optional[AbstractEventBus]:
    topic = os.getenv("AOB_KAFKA_TOPIC", "aob.events")
    bs = os.getenv("AOB_KAFKA_BOOTSTRAP")
    if not bs or KafkaBus is None:
        print("[worker] No Kafka bootstrap; cannot publish outbox.", file=sys.stderr)
        return None
    return KafkaBus(topic=topic, bootstrap_servers=bs)


async def drain_loop(store: AbstractEventStore, bus: AbstractEventBus) -> None:
    base_delay = float(os.getenv("AOB_OUTBOX_POLL_SECS", "1.0"))
    batch = int(os.getenv("AOB_OUTBOX_BATCH", "100"))
    while True:
        try:
            items = await store.fetch_outbox(batch)  # type: ignore[attr-defined]
            if items:
                for evt in items:
                    await bus.publish(evt)
                await store.mark_outbox_delivered([e.id for e in items])  # type: ignore[attr-defined]
                # small jitter after a successful publish burst
                await asyncio.sleep(0.1)
            else:
                # backoff with jitter when idle
                delay = base_delay * (1.0 + random.random())
                await asyncio.sleep(delay)
        except Exception as e:
            # transient error; exponential backoff capped
            print(f"[worker] outbox drain error: {e}", file=sys.stderr)
            await asyncio.sleep(min(10.0, base_delay * 2 * (1.0 + random.random())))


async def main() -> None:
    store = await build_store()
    bus = await build_bus()
    if not store or not bus:
        # keep process alive to allow hot injection of config; periodic log
        while True:
            print("[worker] waiting for store/bus configuration...", file=sys.stderr)
            await asyncio.sleep(15)
    await drain_loop(store, bus)


if __name__ == "__main__":
    asyncio.run(main())
