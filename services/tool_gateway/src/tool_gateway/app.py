"""
Tool Gateway - MCP Proxy with OPA Enforcement

Model Context Protocol server integration with pre/post policy checks, schema validation, and rate limiting.
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from pydantic import BaseModel, Field, ValidationError
import logging
from collections import defaultdict, deque
import jsonschema

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Tool availability status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ToolContract:
    """Tool contract definition"""
    name: str
    description: str
    schema: Dict[str, Any]  # JSON Schema
    endpoint: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    timeout_ms: int = 30000
    rate_limit_per_minute: int = 60
    requires_auth: bool = False
    auth_type: Optional[str] = None  # "bearer", "api_key", "oauth2"
    scopes: List[str] = None
    tags: List[str] = None


@dataclass
class ToolCall:
    """Tool call request"""
    tool_name: str
    parameters: Dict[str, Any]
    correlation_id: str
    tenant_id: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class ToolResponse:
    """Tool call response"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    tool_used: str = ""
    warnings: List[str] = None


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens"""
        async with self.lock:
            now = time.time()
            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class ToolGateway:
    """Tool gateway with MCP proxy and policy enforcement"""
    
    def __init__(self):
        self.tools: Dict[str, ToolContract] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.health_status: Dict[str, ToolStatus] = {}
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # OPA policy evaluator
        self.opa_endpoint = "http://localhost:8181/v1/data/aob/tool_allow"
        
        # Initialize default tools
        self._setup_default_tools()
    
    def _setup_default_tools(self):
        """Setup default tool contracts"""
        # Example: Weather API
        self.tools["weather"] = ToolContract(
            name="weather",
            description="Get current weather information",
            schema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or coordinates"},
                    "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
                },
                "required": ["location"]
            },
            endpoint="https://api.openweathermap.org/data/2.5/weather",
            method="GET",
            rate_limit_per_minute=100,
            requires_auth=True,
            auth_type="api_key",
            tags=["weather", "external"]
        )
        
        # Example: Database query
        self.tools["db_query"] = ToolContract(
            name="db_query",
            description="Execute database query",
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query"},
                    "database": {"type": "string", "description": "Database name"}
                },
                "required": ["query"]
            },
            endpoint="http://localhost:5432/query",
            method="POST",
            rate_limit_per_minute=30,
            requires_auth=True,
            auth_type="bearer",
            scopes=["db:read"],
            tags=["database", "internal"]
        )
        
        # Example: File operations
        self.tools["file_read"] = ToolContract(
            name="file_read",
            description="Read file contents",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "encoding": {"type": "string", "default": "utf-8"}
                },
                "required": ["path"]
            },
            endpoint="http://localhost:9000/files/read",
            method="POST",
            rate_limit_per_minute=60,
            requires_auth=True,
            auth_type="bearer",
            scopes=["files:read"],
            tags=["files", "internal"]
        )
        
        # Initialize rate limiters
        for tool_name, tool in self.tools.items():
            self.rate_limiters[tool_name] = RateLimiter(
                capacity=tool.rate_limit_per_minute,
                refill_rate=tool.rate_limit_per_minute / 60.0
            )
            
            self.health_status[tool_name] = ToolStatus.UNKNOWN
    
    async def check_policy(self, tool_call: ToolCall) -> bool:
        """Check OPA policy for tool call"""
        try:
            policy_input = {
                "tool_name": tool_call.tool_name,
                "tenant_id": tool_call.tenant_id,
                "user_id": tool_call.user_id,
                "parameters": tool_call.parameters,
                "metadata": tool_call.metadata or {}
            }
            
            response = await self._client.post(
                self.opa_endpoint,
                json={"input": policy_input}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result", False)
            else:
                logger.warning(f"OPA policy check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Policy check error: {e}")
            return False
    
    def validate_schema(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Validate parameters against tool schema"""
        if tool_name not in self.tools:
            return [f"Unknown tool: {tool_name}"]
        
        tool = self.tools[tool_name]
        errors = []
        
        try:
            jsonschema.validate(parameters, tool.schema)
        except ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
        
        return errors
    
    async def health_check(self, tool_name: str) -> ToolStatus:
        """Check tool health status"""
        if tool_name not in self.tools:
            return ToolStatus.UNKNOWN
        
        tool = self.tools[tool_name]
        
        try:
            # Simple health check
            health_url = tool.endpoint.replace("/query", "/health").replace("/weather", "/health")
            response = await self._client.get(health_url, timeout=5.0)
            
            if response.status_code == 200:
                status = ToolStatus.HEALTHY
            elif response.status_code in [429, 503]:
                status = ToolStatus.DEGRADED
            else:
                status = ToolStatus.UNHEALTHY
                
        except httpx.TimeoutException:
            status = ToolStatus.DEGRADED
        except Exception:
            status = ToolStatus.UNHEALTHY
        
        self.health_status[tool_name] = status
        return status
    
    async def call_tool(self, tool_call: ToolCall) -> ToolResponse:
        """Execute tool call with all checks"""
        start_time = time.time()
        
        # Check if tool exists
        if tool_call.tool_name not in self.tools:
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {tool_call.tool_name}",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        tool = self.tools[tool_call.tool_name]
        
        # Check health status
        health_status = await self.health_check(tool_call.tool_name)
        if health_status == ToolStatus.UNHEALTHY:
            return ToolResponse(
                success=False,
                error="Tool is currently unhealthy",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Check rate limit
        rate_limiter = self.rate_limiters[tool_call.tool_name]
        if not await rate_limiter.acquire():
            return ToolResponse(
                success=False,
                error="Rate limit exceeded",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Validate schema
        schema_errors = self.validate_schema(tool_call.tool_name, tool_call.parameters)
        if schema_errors:
            return ToolResponse(
                success=False,
                error=f"Schema validation failed: {', '.join(schema_errors)}",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Check OPA policy
        if not await self.check_policy(tool_call):
            return ToolResponse(
                success=False,
                error="Policy check failed",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Execute tool call
        try:
            headers = tool.headers or {}
            
            # Add authentication if required
            if tool.requires_auth:
                if tool.auth_type == "bearer":
                    headers["Authorization"] = f"Bearer {tool_call.metadata.get('auth_token', '')}"
                elif tool.auth_type == "api_key":
                    headers["X-API-Key"] = tool_call.metadata.get('api_key', '')
            
            # Prepare request
            if tool.method == "GET":
                response = await self._client.get(
                    tool.endpoint,
                    params=tool_call.parameters,
                    headers=headers,
                    timeout=tool.timeout_ms / 1000.0
                )
            else:
                response = await self._client.post(
                    tool.endpoint,
                    json=tool_call.parameters,
                    headers=headers,
                    timeout=tool.timeout_ms / 1000.0
                )
            
            response.raise_for_status()
            result = response.json()
            
            latency_ms = (time.time() - start_time) * 1000
            
            return ToolResponse(
                success=True,
                result=result,
                tool_used=tool_call.tool_name,
                latency_ms=latency_ms
            )
            
        except httpx.TimeoutException:
            return ToolResponse(
                success=False,
                error="Tool call timeout",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        except httpx.HTTPStatusError as e:
            return ToolResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code}",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"Tool call failed: {str(e)}",
                tool_used=tool_call.tool_name,
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def register_tool(self, tool: ToolContract) -> bool:
        """Register a new tool"""
        try:
            self.tools[tool.name] = tool
            self.rate_limiters[tool.name] = RateLimiter(
                capacity=tool.rate_limit_per_minute,
                refill_rate=tool.rate_limit_per_minute / 60.0
            )
            self.health_status[tool.name] = ToolStatus.UNKNOWN
            return True
        except Exception as e:
            logger.error(f"Failed to register tool {tool.name}: {e}")
            return False
    
    async def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool gateway statistics"""
        stats = {
            "total_tools": len(self.tools),
            "healthy_tools": sum(1 for status in self.health_status.values() if status == ToolStatus.HEALTHY),
            "tools_by_status": {},
            "tools_by_tag": {}
        }
        
        # Group by status
        for status in self.health_status.values():
            status_name = status.value
            if status_name not in stats["tools_by_status"]:
                stats["tools_by_status"][status_name] = 0
            stats["tools_by_status"][status_name] += 1
        
        # Group by tags
        for tool in self.tools.values():
            for tag in tool.tags or []:
                if tag not in stats["tools_by_tag"]:
                    stats["tools_by_tag"][tag] = 0
                stats["tools_by_tag"][tag] += 1
        
        return stats
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


# Global instance
tool_gateway = ToolGateway()


# FastAPI integration
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Tool Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/tools/call")
async def call_tool_endpoint(tool_call: ToolCall):
    """Tool call endpoint"""
    try:
        response = await tool_gateway.call_tool(tool_call)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": {name: asdict(tool) for name, tool in tool_gateway.tools.items()},
        "health_status": {name: status.value for name, status in tool_gateway.health_status.items()}
    }


@app.post("/tools/register")
async def register_tool_endpoint(tool: ToolContract):
    """Register a new tool"""
    success = await tool_gateway.register_tool(tool)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to register tool")
    return {"status": "registered"}


@app.get("/tools/stats")
async def get_tool_stats():
    """Get tool gateway statistics"""
    return await tool_gateway.get_tool_stats()


@app.get("/tools/{tool_name}/health")
async def check_tool_health(tool_name: str):
    """Check health of a specific tool"""
    status = await tool_gateway.health_check(tool_name)
    return {"tool": tool_name, "status": status.value}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "tools": len(tool_gateway.tools)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)