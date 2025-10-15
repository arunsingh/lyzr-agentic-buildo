from __future__ import annotations
from fastapi import FastAPI

app = FastAPI(title="Metering Service")

_counters: dict[str, float] = {}

@app.post("/tenants/{tenant}/meter")
async def meter(tenant: str, data: dict):
    # data: {metric: value}
    for k, v in data.items():
        key = f"{tenant}:{k}"
        _counters[key] = _counters.get(key, 0.0) + float(v)
    return {"ok": True}

@app.get("/tenants/{tenant}/usage")
async def usage(tenant: str):
    items = {k.split(":",1)[1]: v for k, v in _counters.items() if k.startswith(f"{tenant}:")}
    return {"tenant": tenant, "usage": items}

