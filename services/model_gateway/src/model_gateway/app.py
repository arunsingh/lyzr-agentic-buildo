"""
Model Gateway - vLLM Integration

High-throughput OSS model serving with routing policies for cost/latency/safety-based selection.
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model performance tiers"""
    CHEAP = "cheap"      # Fast, low cost, basic quality
    BALANCED = "balanced"  # Good balance of cost/quality/speed
    QUALITY = "quality"   # High quality, slower, more expensive


class SafetyTier(Enum):
    """Model safety tiers"""
    BASIC = "basic"      # Standard safety measures
    ENHANCED = "enhanced"  # Additional safety checks
    MAXIMUM = "maximum"   # Maximum safety, restricted outputs


@dataclass
class ModelProfile:
    """Model configuration profile"""
    name: str
    tier: ModelTier
    safety_tier: SafetyTier
    max_tokens: int
    max_latency_ms: int
    cost_per_1k_tokens: float
    endpoint: str
    api_key: Optional[str] = None
    context_window: int = 4096
    supports_streaming: bool = True
    supports_function_calling: bool = False


@dataclass
class RoutingPolicy:
    """Model routing policy"""
    max_latency_ms: int = 5000
    max_cost_usd: float = 1.0
    preferred_tier: Optional[ModelTier] = None
    required_safety_tier: SafetyTier = SafetyTier.BASIC
    allow_fallback: bool = True


class ModelRequest(BaseModel):
    """Model inference request"""
    prompt: str
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False
    functions: Optional[List[Dict[str, Any]]] = None
    safety_checks: bool = True


class ModelResponse(BaseModel):
    """Model inference response"""
    text: str
    model_used: str
    tokens_used: int
    cost_usd: float
    latency_ms: float
    safety_score: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)


class ModelGateway:
    """Model gateway with routing and load balancing"""
    
    def __init__(self):
        self.models: Dict[str, ModelProfile] = {}
        self.routing_cache: Dict[str, str] = {}
        self.health_status: Dict[str, bool] = {}
        self._client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize default models
        self._setup_default_models()
    
    def _setup_default_models(self):
        """Setup default model profiles"""
        # vLLM models (local)
        self.models["llama-7b"] = ModelProfile(
            name="llama-7b",
            tier=ModelTier.CHEAP,
            safety_tier=SafetyTier.BASIC,
            max_tokens=2048,
            max_latency_ms=3000,
            cost_per_1k_tokens=0.001,
            endpoint="http://localhost:8001/v1/completions",
            context_window=4096,
            supports_streaming=True,
            supports_function_calling=False
        )
        
        self.models["llama-13b"] = ModelProfile(
            name="llama-13b",
            tier=ModelTier.BALANCED,
            safety_tier=SafetyTier.BASIC,
            max_tokens=2048,
            max_latency_ms=5000,
            cost_per_1k_tokens=0.002,
            endpoint="http://localhost:8001/v1/completions",
            context_window=4096,
            supports_streaming=True,
            supports_function_calling=False
        )
        
        # Hosted models (examples)
        self.models["gpt-3.5-turbo"] = ModelProfile(
            name="gpt-3.5-turbo",
            tier=ModelTier.BALANCED,
            safety_tier=SafetyTier.ENHANCED,
            max_tokens=4096,
            max_latency_ms=2000,
            cost_per_1k_tokens=0.002,
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-...",  # Would come from environment
            context_window=4096,
            supports_streaming=True,
            supports_function_calling=True
        )
        
        self.models["gpt-4"] = ModelProfile(
            name="gpt-4",
            tier=ModelTier.QUALITY,
            safety_tier=SafetyTier.MAXIMUM,
            max_tokens=8192,
            max_latency_ms=10000,
            cost_per_1k_tokens=0.03,
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-...",  # Would come from environment
            context_window=8192,
            supports_streaming=True,
            supports_function_calling=True
        )
    
    async def health_check(self, model_name: str) -> bool:
        """Check if a model is healthy and available"""
        if model_name not in self.models:
            return False
        
        model = self.models[model_name]
        
        try:
            # Simple health check request
            response = await self._client.get(f"{model.endpoint.replace('/completions', '/health')}")
            is_healthy = response.status_code == 200
            self.health_status[model_name] = is_healthy
            return is_healthy
        except Exception as e:
            logger.warning(f"Health check failed for {model_name}: {e}")
            self.health_status[model_name] = False
            return False
    
    def select_model(self, policy: RoutingPolicy, request: ModelRequest) -> Optional[str]:
        """Select the best model based on routing policy"""
        cache_key = f"{policy.max_latency_ms}:{policy.max_cost_usd}:{policy.preferred_tier}:{policy.required_safety_tier}"
        
        if cache_key in self.routing_cache:
            return self.routing_cache[cache_key]
        
        # Filter models by policy constraints
        candidates = []
        
        for name, model in self.models.items():
            # Check health status
            if not self.health_status.get(name, True):
                continue
            
            # Check latency constraint
            if model.max_latency_ms > policy.max_latency_ms:
                continue
            
            # Check safety tier
            if model.safety_tier.value < policy.required_safety_tier.value:
                continue
            
            # Estimate cost
            estimated_tokens = len(request.prompt.split()) * 1.3  # Rough estimate
            estimated_cost = (estimated_tokens / 1000) * model.cost_per_1k_tokens
            
            if estimated_cost > policy.max_cost_usd:
                continue
            
            candidates.append((name, model, estimated_cost))
        
        if not candidates:
            if policy.allow_fallback:
                # Fallback to cheapest available model
                candidates = [(name, model, 0) for name, model in self.models.items() 
                             if self.health_status.get(name, True)]
                candidates.sort(key=lambda x: x[1].cost_per_1k_tokens)
            else:
                return None
        
        # Sort by preference
        if policy.preferred_tier:
            candidates.sort(key=lambda x: (
                0 if x[1].tier == policy.preferred_tier else 1,
                x[2]  # cost
            ))
        else:
            # Sort by cost
            candidates.sort(key=lambda x: x[2])
        
        selected_model = candidates[0][0]
        self.routing_cache[cache_key] = selected_model
        return selected_model
    
    async def infer(self, request: ModelRequest, policy: Optional[RoutingPolicy] = None) -> ModelResponse:
        """Perform model inference with routing"""
        if policy is None:
            policy = RoutingPolicy()
        
        # Select model
        model_name = self.select_model(policy, request)
        if not model_name:
            raise ValueError("No suitable model found for the given policy")
        
        model = self.models[model_name]
        
        # Prepare request
        start_time = time.time()
        
        # Calculate actual tokens (rough estimate)
        tokens_used = len(request.prompt.split()) * 1.3
        cost_usd = (tokens_used / 1000) * model.cost_per_1k_tokens
        
        # Prepare API request
        api_request = {
            "prompt": request.prompt,
            "max_tokens": request.max_tokens or model.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream and model.supports_streaming
        }
        
        headers = {"Content-Type": "application/json"}
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"
        
        try:
            # Make API call
            response = await self._client.post(
                model.endpoint,
                json=api_request,
                headers=headers
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Extract text (format varies by provider)
            if "choices" in data:
                text = data["choices"][0]["text"]
            elif "content" in data:
                text = data["content"]
            else:
                text = str(data)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Safety scoring (placeholder)
            safety_score = None
            warnings = []
            
            if request.safety_checks:
                safety_score = self._calculate_safety_score(text)
                if safety_score < 0.7:
                    warnings.append("Low safety score detected")
            
            return ModelResponse(
                text=text,
                model_used=model_name,
                tokens_used=int(tokens_used),
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                safety_score=safety_score,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Model inference failed for {model_name}: {e}")
            raise
    
    def _calculate_safety_score(self, text: str) -> float:
        """Calculate safety score for generated text (placeholder implementation)"""
        # This would integrate with actual safety scoring models
        # For now, return a random score
        import random
        return random.uniform(0.5, 1.0)
    
    async def warm_model(self, model_name: str) -> bool:
        """Warm up a model for faster inference"""
        if model_name not in self.models:
            return False
        
        try:
            # Send a warm-up request
            warm_request = ModelRequest(
                prompt="Hello, this is a warm-up request.",
                max_tokens=10
            )
            
            await self.infer(warm_request, RoutingPolicy(max_latency_ms=30000))
            logger.info(f"Model {model_name} warmed up successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to warm up model {model_name}: {e}")
            return False
    
    async def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about available models"""
        stats = {
            "total_models": len(self.models),
            "healthy_models": sum(1 for healthy in self.health_status.values() if healthy),
            "models_by_tier": {},
            "models_by_safety": {},
            "total_cost_per_1k": sum(model.cost_per_1k_tokens for model in self.models.values())
        }
        
        # Group by tier
        for model in self.models.values():
            tier = model.tier.value
            if tier not in stats["models_by_tier"]:
                stats["models_by_tier"][tier] = 0
            stats["models_by_tier"][tier] += 1
        
        # Group by safety tier
        for model in self.models.values():
            safety = model.safety_tier.value
            if safety not in stats["models_by_safety"]:
                stats["models_by_safety"][safety] = 0
            stats["models_by_safety"][safety] += 1
        
        return stats
    
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


# Global instance
model_gateway = ModelGateway()


# FastAPI integration
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Model Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/infer")
async def infer_endpoint(
    request: ModelRequest,
    policy: Optional[RoutingPolicy] = None,
    background_tasks: BackgroundTasks = None
):
    """Model inference endpoint"""
    try:
        response = await model_gateway.infer(request, policy)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def list_models():
    """List available models"""
    return {
        "models": {name: asdict(model) for name, model in model_gateway.models.items()},
        "health_status": model_gateway.health_status
    }


@app.get("/stats")
async def get_stats():
    """Get model gateway statistics"""
    return await model_gateway.get_model_stats()


@app.post("/warm/{model_name}")
async def warm_model(model_name: str):
    """Warm up a specific model"""
    success = await model_gateway.warm_model(model_name)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"status": "warmed"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "models": len(model_gateway.models)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8087)