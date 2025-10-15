
from __future__ import annotations
import asyncio, json
from typing import AsyncIterator
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from agentic_core.bus import AbstractEventBus
from agentic_core.events import Event

class KafkaBus(AbstractEventBus):
    def __init__(self, topic: str, bootstrap_servers: str, group_id: str = "aob"):
        self.topic, self.bootstrap_servers, self.group_id = topic, bootstrap_servers, group_id
        self._producer: AIOKafkaProducer | None = None
        self._consumer: AIOKafkaConsumer | None = None

    async def _ensure(self):
        if not self._producer:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
            await self._producer.start()
        if not self._consumer:
            self._consumer = AIOKafkaConsumer(self.topic, bootstrap_servers=self.bootstrap_servers, group_id=self.group_id, enable_auto_commit=True, auto_offset_reset="earliest")
            await self._consumer.start()

    async def publish(self, evt: Event) -> None:
        await self._ensure()
        await self._producer.send_and_wait(self.topic, json.dumps(evt.to_dict()).encode())

    async def subscribe(self) -> AsyncIterator[Event]:
        await self._ensure()
        try:
            async for msg in self._consumer:
                data = json.loads(msg.value.decode())
                yield Event(**data)
        finally:
            await asyncio.gather(self._consumer.stop(), return_exceptions=True)
