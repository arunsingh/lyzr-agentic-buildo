"""
Agentic Orchestration Builder - Python SDK

A comprehensive Python SDK for the AOB platform with streaming, retries, and HITL helpers.
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import httpx
from pydantic import BaseModel


class AuthMethod(Enum):
    """Authentication methods supported by the SDK"""
    OIDC = "oidc"
    API_KEY = "api_key"


@dataclass
class AuthConfig:
    """Authentication configuration"""
    method: AuthMethod
    token: Optional[str] = None
    api_key: Optional[str] = None
    tenant: Optional[str] = None


class WorkflowStatus(Enum):
    """Workflow execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowEvent:
    """Workflow event representation"""
    type: str
    payload: Dict[str, Any]
    timestamp: float
    correlation_id: str
    node_id: Optional[str] = None


@dataclass
class DecisionRecord:
    """Decision record from audit trail"""
    correlation_id: str
    workflow_id: str
    node_id: str
    node_name: str
    node_kind: str
    allowed: bool
    policies_applied: List[str]
    input_snapshot: Dict[str, Any]
    output_snapshot: Dict[str, Any]
    model_info: Dict[str, Any]
    tool_calls: List[Dict[str, Any]]
    cost: Dict[str, Any]
    latency_ms: Optional[float] = None
    timestamp: Optional[str] = None


class AOBClient:
    """Main AOB SDK client"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth: Optional[AuthConfig] = None):
        self.base_url = base_url.rstrip('/')
        self.auth = auth or AuthConfig(method=AuthMethod.API_KEY, api_key="demo:local-dev-key")
        self._client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.auth.method == AuthMethod.OIDC and self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        elif self.auth.method == AuthMethod.API_KEY and self.auth.api_key:
            headers["X-API-Key"] = self.auth.api_key
        
        return headers
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information and available endpoints"""
        response = await self._client.get(f"{self.base_url}/", headers=self._get_headers())
        response.raise_for_status()
        return response.json()
    
    async def compile_workflow(self, yaml_content: str) -> Dict[str, Any]:
        """Compile a workflow from YAML"""
        response = await self._client.post(
            f"{self.base_url}/workflows/compile",
            headers=self._get_headers(),
            json={"yaml": yaml_content}
        )
        response.raise_for_status()
        return response.json()
    
    async def start_workflow(self, workflow_id: str, **kwargs) -> Dict[str, Any]:
        """Start a workflow execution"""
        payload = {"workflow_id": workflow_id, **kwargs}
        response = await self._client.post(
            f"{self.base_url}/workflows/start",
            headers=self._get_headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def resume_workflow(self, workflow_id: str, approval: bool = True) -> Dict[str, Any]:
        """Resume a paused workflow"""
        response = await self._client.post(
            f"{self.base_url}/workflows/resume",
            headers=self._get_headers(),
            json={"workflow_id": workflow_id, "approval": approval}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_workflow_events(self, correlation_id: str) -> List[WorkflowEvent]:
        """Get workflow events"""
        response = await self._client.get(
            f"{self.base_url}/workflows/{correlation_id}/events",
            headers=self._get_headers()
        )
        response.raise_for_status()
        data = response.json()
        
        events = []
        for item in data.get("items", []):
            events.append(WorkflowEvent(
                type=item["type"],
                payload=item["payload"],
                timestamp=item["ts"],
                correlation_id=item["correlation_id"],
                node_id=item["payload"].get("node")
            ))
        
        return events
    
    async def stream_workflow_events(self, correlation_id: str, poll_interval: float = 1.0) -> AsyncGenerator[WorkflowEvent, None]:
        """Stream workflow events in real-time"""
        seen_events = set()
        
        while True:
            events = await self.get_workflow_events(correlation_id)
            
            for event in events:
                event_key = f"{event.type}:{event.timestamp}:{event.correlation_id}"
                if event_key not in seen_events:
                    seen_events.add(event_key)
                    yield event
            
            await asyncio.sleep(poll_interval)
    
    async def create_snapshot(self, correlation_id: str) -> Dict[str, Any]:
        """Create a workflow snapshot"""
        response = await self._client.post(
            f"{self.base_url}/workflows/{correlation_id}/snapshots",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_snapshots(self, correlation_id: str) -> List[Dict[str, Any]]:
        """List available snapshots for a workflow"""
        response = await self._client.get(
            f"{self.base_url}/workflows/{correlation_id}/snapshots",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json().get("snapshots", [])
    
    async def replay_workflow(self, correlation_id: str, snapshot_id: str) -> Dict[str, Any]:
        """Replay a workflow from a snapshot"""
        response = await self._client.post(
            f"{self.base_url}/workflows/{correlation_id}/replay",
            headers=self._get_headers(),
            params={"snapshot_id": snapshot_id}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_audit_records(self, correlation_id: Optional[str] = None) -> List[DecisionRecord]:
        """Get audit records (DecisionRecords)"""
        # This would connect to the audit service
        audit_url = "http://localhost:8001"
        response = await self._client.get(
            f"{audit_url}/decisions",
            headers=self._get_headers()
        )
        response.raise_for_status()
        data = response.json()
        
        records = []
        for item in data.get("items", []):
            if correlation_id and item["correlation_id"] != correlation_id:
                continue
                
            records.append(DecisionRecord(
                correlation_id=item["correlation_id"],
                workflow_id=item["workflow_id"],
                node_id=item["node_id"],
                node_name=item["node_name"],
                node_kind=item["node_kind"],
                allowed=item["allowed"],
                policies_applied=item["policies_applied"],
                input_snapshot=item["input_snapshot"],
                output_snapshot=item["output_snapshot"],
                model_info=item["model_info"],
                tool_calls=item["tool_calls"],
                cost=item["cost"],
                latency_ms=item.get("latency_ms"),
                timestamp=item.get("timestamp")
            ))
        
        return records
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


class HITLHelper:
    """Human-in-the-Loop helper for workflow management"""
    
    def __init__(self, client: AOBClient):
        self.client = client
    
    async def wait_for_approval(self, correlation_id: str, timeout: float = 300.0) -> bool:
        """Wait for human approval on a workflow"""
        start_time = time.time()
        
        async for event in self.client.stream_workflow_events(correlation_id):
            if event.type == "human.approved":
                return True
            elif event.type == "human.rejected":
                return False
            elif time.time() - start_time > timeout:
                raise TimeoutError(f"Approval timeout after {timeout}s")
        
        return False
    
    async def approve_workflow(self, correlation_id: str) -> Dict[str, Any]:
        """Approve a paused workflow"""
        return await self.client.resume_workflow(correlation_id, approval=True)
    
    async def reject_workflow(self, correlation_id: str) -> Dict[str, Any]:
        """Reject a paused workflow"""
        return await self.client.resume_workflow(correlation_id, approval=False)


class RetryHelper:
    """Retry helper with exponential backoff"""
    
    @staticmethod
    async def with_retry(
        func,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        """Execute function with retry logic"""
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                if jitter:
                    delay *= (0.5 + 0.5 * time.time() % 1)  # Add jitter
                
                await asyncio.sleep(delay)


# Convenience functions
async def create_client(
    base_url: str = "http://localhost:8000",
    oidc_token: Optional[str] = None,
    api_key: Optional[str] = None,
    tenant: Optional[str] = None
) -> AOBClient:
    """Create an AOB client with authentication"""
    if oidc_token:
        auth = AuthConfig(method=AuthMethod.OIDC, token=oidc_token, tenant=tenant)
    else:
        auth = AuthConfig(method=AuthMethod.API_KEY, api_key=api_key or "demo:local-dev-key")
    
    return AOBClient(base_url, auth)


# Example usage
async def example_usage():
    """Example of how to use the AOB SDK"""
    client = await create_client()
    
    # Start a workflow
    result = await client.start_workflow("example-workflow", text="Hello AOB!")
    correlation_id = result["correlation_id"]
    
    # Stream events
    async for event in client.stream_workflow_events(correlation_id):
        print(f"Event: {event.type} - {event.payload}")
        
        if event.type == "workflow.completed":
            break
    
    # Get audit records
    records = await client.get_audit_records(correlation_id)
    for record in records:
        print(f"Decision: {record.node_name} - Allowed: {record.allowed}")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
