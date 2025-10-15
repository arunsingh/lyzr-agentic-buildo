from __future__ import annotations
from typing import Any, Dict, List

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


class OpaPolicyEvaluator:
    def __init__(self, base_url: str | None = None, decision_path: str = "aob/allow"):
        self.base_url = (base_url or "http://localhost:8181").rstrip("/")
        self.decision_path = decision_path.strip("/")

    async def evaluate(self, input_doc: Dict[str, Any]) -> bool:
        if httpx is None:
            policies = input_doc.get("policies", [])
            return "deny_all" not in policies
        url = f"{self.base_url}/v1/data/{self.decision_path}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json={"input": input_doc})
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result")
            if isinstance(result, dict):
                return bool(result.get("allow", True))
            return bool(result)

