
from __future__ import annotations
from typing import List, Optional, Callable
from .events import Event
from .bus import AbstractEventBus
from .store import AbstractEventStore
from .nodes import BaseNode, Context
from .types import DecisionRecord
from .policy import OpaPolicyEvaluator
from .otel import span


class PolicyGuard:
    def __init__(self, evaluator: Optional[OpaPolicyEvaluator] = None,
                 check_fn: Optional[Callable[[Context, BaseNode, List[str], dict], bool]] = None):
        self._evaluator = evaluator or OpaPolicyEvaluator()
        self._check_fn = check_fn

    async def check(self, ctx: Context, node: BaseNode, policies: List[str], edge: dict) -> bool:
        if self._check_fn:
            return self._check_fn(ctx, node, policies, edge)
        input_doc = {
            "node": {"id": node.id, "name": node.name, "kind": type(node).__name__},
            "ctx": {"bag": ctx.bag},
            "policies": policies,
            "edge": edge,
        }
        return await self._evaluator.evaluate(input_doc)

class Workflow:
    def __init__(self, id: str, nodes: List[BaseNode], edges: Optional[List[dict]] = None):
        self.id, self.nodes = id, nodes
        self.edges = edges or []

    def policies_for(self, node_id: str) -> List[str]:
        return [p for e in self.edges for p in e.get("policies", []) if e.get("to") == node_id]

class WorkflowEngine:
    def __init__(self, bus: AbstractEventBus, store: AbstractEventStore, *, policy: Optional[PolicyGuard] = None, on_decision: Optional[Callable[[DecisionRecord], None]] = None):
        self.bus, self.store = bus, store
        evaluator = OpaPolicyEvaluator()
        self.policy = policy or PolicyGuard(check_fn=lambda ctx, node, policies: True)
        self.on_decision = on_decision

    async def start(self, wf: Workflow, ctx: Context) -> str:
        correlation_id = ctx.bag.setdefault("correlation_id", wf.id)
        for node in wf.nodes:
            with span(f"node:{node.id}"):
                policies = wf.policies_for(node.id)
                edge = next((e for e in wf.edges if e.get("to") == node.id), {})
                allowed = await self.policy.check(ctx, node, policies, edge)
                if not allowed:
                    evt = Event.new("policy.denied", {"node": node.id, "reason": "policy"})
                    await self.store.append(evt); await self.bus.publish(evt)
                    break
                evt = await node.run(ctx)
            evt = Event.new(evt.type, {**evt.payload, "workflow": wf.id},
                            correlation_id=correlation_id, causation_id=evt.id)
            await self.store.append(evt); await self.bus.publish(evt)
            if self.on_decision:
                dr = DecisionRecord(
                    correlation_id=correlation_id,
                    workflow_id=wf.id,
                    node_id=node.id,
                    node_name=node.name,
                    node_kind=type(node).__name__,
                    allowed=True,
                    policies_applied=wf.policies_for(node.id),
                    input_snapshot=dict(ctx.bag),
                    output_snapshot=evt.payload,
                    model_info={}, tool_calls=[], cost={}, latency_ms=None,
                )
                self.on_decision(dr)
            if evt.type == "human.wait": break
        return correlation_id

    async def resume(self, wf: Workflow, ctx: Context) -> str:
        cid = ctx.bag["correlation_id"]
        done = {e.payload.get("node") for e in await self.store.list(cid)
                if e.type in {"task.completed", "agent.completed", "human.approved"}}
        for node in wf.nodes:
            if node.id in done: continue
            with span(f"node:{node.id}"):
                policies = wf.policies_for(node.id)
                edge = next((e for e in wf.edges if e.get("to") == node.id), {})
                allowed = await self.policy.check(ctx, node, policies, edge)
                if not allowed:
                    evt = Event.new("policy.denied", {"node": node.id, "reason": "policy"}, correlation_id=cid)
                    await self.store.append(evt); await self.bus.publish(evt)
                    break
                evt = await node.run(ctx)
            evt = Event.new(evt.type, {**evt.payload, "workflow": wf.id}, correlation_id=cid)
            await self.store.append(evt); await self.bus.publish(evt)
            if self.on_decision:
                dr = DecisionRecord(
                    correlation_id=cid,
                    workflow_id=wf.id,
                    node_id=node.id,
                    node_name=node.name,
                    node_kind=type(node).__name__,
                    allowed=True,
                    policies_applied=wf.policies_for(node.id),
                    input_snapshot=dict(ctx.bag),
                    output_snapshot=evt.payload,
                    model_info={}, tool_calls=[], cost={}, latency_ms=None,
                )
                self.on_decision(dr)
            if evt.type == "human.wait": break
        return cid
