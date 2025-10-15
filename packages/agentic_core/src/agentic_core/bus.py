
from __future__ import annotations
import asyncio
from typing import AsyncIterator
from .events import Event

class AbstractEventBus:
    async def publish(self, evt: Event) -> None: ...
    async def subscribe(self) -> AsyncIterator[Event]: ...

class InMemoryBus(AbstractEventBus):
    def __init__(self, maxsize: int = 1000):
        self._q: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)

    async def publish(self, evt: Event) -> None:
        await self._q.put(evt)

    async def subscribe(self) -> AsyncIterator[Event]:
        while True:
            evt = await self._q.get()
            yield evt
            self._q.task_done()
