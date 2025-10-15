
from __future__ import annotations
from pydantic import BaseModel
from typing import List, Literal, Dict, Any, Callable, Optional
import yaml
from .nodes import TaskNode, AgentNode, HumanCheckpointNode, BaseNode, Context
from .engine import Workflow

NodeKind = Literal["task", "agent", "human"]

class NodeSpec(BaseModel):
    id: str
    name: str
    kind: NodeKind
    # For demo: simple expressions instead of dynamic import
    expr: str | None = None
    approval_key: str | None = None

class WorkflowSpec(BaseModel):
    id: str
    nodes: List[NodeSpec]
    edges: Optional[List[Dict[str, Any]]] = None
    # per-edge optional retry/backoff config

def _mk_fn(expr: str) -> Callable[[Context], Dict[str, Any]]:
    # extremely limited, safe expression evaluator (demo only)
    def fn(ctx: Context):
        return {"value": eval(expr, {"__builtins__": {}}, {"ctx": ctx})}  # noqa: S307 (demo)
    return fn

def compile_workflow(spec: WorkflowSpec) -> Workflow:
    nodes: List[BaseNode] = []
    for ns in spec.nodes:
        if ns.kind == "task":
            nodes.append(TaskNode(ns.id, ns.name, _mk_fn(ns.expr or "ctx.bag")))
        elif ns.kind == "agent":
            nodes.append(AgentNode(ns.id, ns.name, _mk_fn(ns.expr or "ctx.bag")))
        else:
            nodes.append(HumanCheckpointNode(ns.id, ns.name, ns.approval_key or "approval"))
    # Attach edge list with policies onto the Workflow for policy evaluation
    edges = spec.edges or []
    return Workflow(id=spec.id, nodes=nodes, edges=edges)

def load_workflow_yaml(yaml_text: str) -> Workflow:
    data = yaml.safe_load(yaml_text)
    return compile_workflow(WorkflowSpec(**data))
