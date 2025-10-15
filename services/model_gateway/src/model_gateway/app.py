from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Model Gateway")

class InferenceReq(BaseModel):
    model: str
    prompt: str
    params: dict | None = None

@app.post("/infer")
async def infer(req: InferenceReq):
    # Placeholder: route to vLLM/hosted provider based on model
    return {"model": req.model, "output": req.prompt[:128]}

