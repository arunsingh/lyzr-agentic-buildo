
import pytest, asyncio
from agentic_core import InMemoryBus, InMemoryStore, WorkflowEngine, Context, Workflow, TaskNode, HumanCheckpointNode

@pytest.mark.asyncio
async def test_human_checkpoint_resume():
    bus, store = InMemoryBus(), InMemoryStore()
    engine = WorkflowEngine(bus, store)
    wf = Workflow(
        id="t1",
        nodes=[
            TaskNode("n1","t1", lambda ctx: {"ok": True}),
            HumanCheckpointNode("n2","review","approval"),
            TaskNode("n3","t2", lambda ctx: {"done": True}),
        ],
    )
    ctx = Context(bag={"approval": False})
    cid = await engine.start(wf, ctx)
    evts = [e.type for e in await store.list(cid)]
    assert "human.wait" in evts and "task.completed" in evts

    ctx.bag["approval"] = True
    await engine.resume(wf, ctx)
    evts2 = [e.type for e in await store.list(cid)]
    assert "human.approved" in evts2 and evts2.count("task.completed") == 2
