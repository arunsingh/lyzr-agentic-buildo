
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional
from .events import Event

@dataclass
class Context:
    bag: Dict[str, Any]

class BaseNode:
    id: str
    name: str
    def __init__(self, id: str, name: str):
        self.id, self.name = id, name

    async def run(self, ctx: Context) -> Event:
        raise NotImplementedError

    def compensation(self) -> Optional[Callable[[Context], Event]]:
        return None

class TaskNode(BaseNode):
    def __init__(self, id: str, name: str, fn: Callable[[Context], Dict[str, Any]]):
        super().__init__(id, name); self.fn = fn
    async def run(self, ctx: Context) -> Event:
        out = self.fn(ctx)
        return Event.new("task.completed", {"node": self.id, "out": out})

class AgentNode(BaseNode):
    def __init__(self, id: str, name: str, agent: Callable[[Context], Dict[str, Any]]):
        super().__init__(id, name); self.agent = agent
    async def run(self, ctx: Context) -> Event:
        out = self.agent(ctx)
        return Event.new("agent.completed", {"node": self.id, "out": out})

class HumanCheckpointNode(BaseNode):
    def __init__(self, id: str, name: str, approval_key: str):
        super().__init__(id, name); self.approval_key = approval_key
    async def run(self, ctx: Context) -> Event:
        if ctx.bag.get(self.approval_key) is True:
            return Event.new("human.approved", {"node": self.id})
        return Event.new("human.wait", {"node": self.id})
