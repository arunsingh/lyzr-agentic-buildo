
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agentic_core import InMemoryBus, InMemoryStore, WorkflowEngine, Context, Workflow, TaskNode, AgentNode, HumanCheckpointNode
from agentic_core.types import AgentSpec
from agentic_core.audit import HttpAuditSink
from agentic_core.otel import init as otel_init
from agentic_core.compiler import load_workflow_yaml

app = FastAPI(title="Agentic Orchestration Builder API")

bus, store = InMemoryBus(), InMemoryStore()
audit = HttpAuditSink()
engine = WorkflowEngine(bus, store, on_decision=audit.emit)

# Initialize OTEL if available
try:
    otel_init()
except Exception:
    pass

# default demo workflow (can be replaced via YAML upload)
wf = Workflow(
    id="demo",
    nodes=[
        TaskNode("n1", "uppercase", lambda ctx: {"text": ctx.bag["text"].upper()}),
        AgentNode("n2", "summarize", lambda ctx: {"summary": ctx.bag["text"][:10]}),
        HumanCheckpointNode("n3", "review", approval_key="approval"),
        TaskNode("n4", "ship", lambda ctx: {"status": "done"}),
    ],
)

class StartReq(BaseModel):
    workflow_id: str
    text: str = "hello agentic"
    approval: bool = False

class ResumeReq(BaseModel):
    workflow_id: str
    approval: bool = True

class CompileReq(BaseModel):
    yaml: str

class CreateAgentReq(BaseModel):
    spec: AgentSpec

@app.get("/")
async def root():
    return {"_links": {
        "self": {"href": "/"},
        "start": {"href": "/workflows/start", "method": "POST"},
        "resume": {"href": "/workflows/resume", "method": "POST"},
        "compile": {"href": "/workflows/compile", "method": "POST"},
        "agents": {"href": "/agents", "method": "POST"},
        "invocations": {"href": "/invocations", "method": "POST"},
        "sessions": {"href": "/sessions", "method": "POST"}
    }}

@app.post("/workflows/start")
async def start(req: StartReq):
    ctx = Context(bag={"text": req.text, "approval": req.approval, "correlation_id": req.workflow_id})
    cid = await engine.start(wf, ctx)
    return {"correlation_id": cid, "_links": {"events": {"href": f"/workflows/{cid}/events"}, "resume": {"href": "/workflows/resume", "method": "POST"}}}

@app.post("/workflows/resume")
async def resume(req: ResumeReq):
    ctx = Context(bag={"approval": req.approval, "correlation_id": req.workflow_id})
    cid = await engine.resume(wf, ctx)
    return {"correlation_id": cid, "_links": {"events": {"href": f"/workflows/{cid}/events"}}}

@app.get("/workflows/{cid}/events")
async def events(cid: str):
    evts = [e.to_dict() for e in await store.list(cid)]
    return {"count": len(evts), "items": evts, "_links": {"self": {"href": f"/workflows/{cid}/events"}}}

@app.post("/workflows/compile")
async def compile_yaml(req: CompileReq):
    global wf
    try:
        wf = load_workflow_yaml(req.yaml)
        return {"status": "ok", "workflow_id": wf.id}
    except Exception as e:
        raise HTTPException(400, f"Invalid YAML: {e}")

# Minimal AaaS surface (in-memory only for now)
_agents: dict[str, AgentSpec] = {}

@app.post("/agents")
async def create_agent(req: CreateAgentReq):
    spec = req.spec
    key = f"{spec.id}:{spec.version}"
    _agents[key] = spec
    return {"id": spec.id, "version": spec.version, "owner": spec.owner}

class InvocationReq(BaseModel):
    agent_id: str
    version: str
    input: dict

@app.post("/invocations")
async def invoke(req: InvocationReq):
    # Demo: route to current wf and pass input bag; real impl looks up AgentSpec
    ctx = Context(bag={**req.input, "correlation_id": req.agent_id})
    cid = await engine.start(wf, ctx)
    return {"correlation_id": cid}

class SessionReq(BaseModel):
    agent_id: str
    input: dict

@app.post("/sessions")
async def create_session(req: SessionReq):
    # Demo session id = agent_id for simplicity
    return {"session_id": req.agent_id, "_links": {"events": {"href": f"/workflows/{req.agent_id}/events"}}}
