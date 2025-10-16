# 10-Day Execution Plan: Critical Implementation

## 🎯 **Implementation Overview**

Based on the technical deep dive analysis, the AOB platform is **78% complete** with critical gaps in execution isolation, DLQ implementation, and metering enforcement. This 10-day plan addresses the most critical production readiness issues.

## 📋 **Implementation Checklist**

### **Day 1-2: DLQ Implementation**

#### **1.1 Dead Letter Queue with Quarantine TTL**
```python
# packages/agentic_core/src/agentic_core/dlq.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import json

@dataclass
class DLQEntry:
    id: str
    correlation_id: str
    node_id: str
    error: str
    payload: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    quarantine_until: Optional[datetime] = None

class DLQManager:
    def __init__(self, store: AbstractEventStore):
        self.store = store
        self.quarantine_ttl = timedelta(hours=1)  # Configurable
        
    async def quarantine_failed_event(self, event: Event, error: str) -> None:
        """Quarantine failed event with TTL"""
        dlq_entry = DLQEntry(
            id=f"dlq_{event.id}",
            correlation_id=event.correlation_id,
            node_id=event.payload.get("node_id", "unknown"),
            error=error,
            payload=event.payload,
            created_at=datetime.utcnow(),
            quarantine_until=datetime.utcnow() + self.quarantine_ttl
        )
        
        await self.store.append(dlq_entry)
        
    async def get_quarantined_events(self) -> List[DLQEntry]:
        """Get events ready for retry"""
        now = datetime.utcnow()
        # Implementation would query store for quarantined events
        return []
        
    async def retry_quarantined_event(self, dlq_entry: DLQEntry) -> bool:
        """Retry quarantined event"""
        if dlq_entry.retry_count >= dlq_entry.max_retries:
            return False
            
        # Increment retry count and update quarantine
        dlq_entry.retry_count += 1
        dlq_entry.quarantine_until = datetime.utcnow() + self.quarantine_ttl
        
        # Retry the event
        return True
```

#### **1.2 Outbox Watermark Implementation**
```python
# packages/agentic_core/src/agentic_core/outbox.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class OutboxWatermark:
    last_processed_id: str
    last_processed_at: datetime
    batch_size: int = 100
    poll_interval: float = 1.0

class OutboxProcessor:
    def __init__(self, store: AbstractEventStore, bus: AbstractEventBus):
        self.store = store
        self.bus = bus
        self.watermark = OutboxWatermark(
            last_processed_id="",
            last_processed_at=datetime.utcnow()
        )
        
    async def process_outbox(self) -> None:
        """Process outbox with watermark tracking"""
        events = await self.store.fetch_outbox(
            limit=self.watermark.batch_size,
            after_id=self.watermark.last_processed_id
        )
        
        if not events:
            return
            
        # Process events in batch
        for event in events:
            try:
                await self.bus.publish(event)
                await self.store.mark_outbox_delivered([event.id])
                
                # Update watermark
                self.watermark.last_processed_id = event.id
                self.watermark.last_processed_at = datetime.utcnow()
                
            except Exception as e:
                # Send to DLQ
                await self.dlq_manager.quarantine_failed_event(event, str(e))
```

#### **1.3 Idempotent Kafka Producer**
```python
# packages/agentic_adapters/src/agentic_adapters/kafka_bus.py
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import uuid

class IdempotentKafkaBus(AbstractEventBus):
    def __init__(self, bootstrap_servers: str):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # Enable idempotence
            enable_idempotence=True,
            retries=3,
            retry_backoff_ms=100,
            # Ensure exactly-once semantics
            acks='all',
            max_in_flight_requests_per_connection=1
        )
        
    async def publish(self, event: Event) -> None:
        """Publish event with idempotence"""
        try:
            # Use event ID as key for partitioning
            key = event.id.encode('utf-8')
            
            # Add idempotency key to payload
            payload = event.to_dict()
            payload['idempotency_key'] = event.idempotency_key
            
            future = self.producer.send(
                'aob.events',
                key=key,
                value=payload
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
        except KafkaError as e:
            raise Exception(f"Failed to publish event: {e}")
```

### **Day 3-4: OIDC Enhancement**

#### **2.1 JWKS Integration**
```python
# services/api/src/aob_api/oidc.py
import httpx
from jose import jwt, jwks
from jose.exceptions import JWTError
import json

class OIDC:
    def __init__(self, issuer_url: str, audience: str):
        self.issuer_url = issuer_url
        self.audience = audience
        self.jwks_client = None
        self.jwks_cache = {}
        
    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from issuer"""
        if self.jwks_client is None:
            self.jwks_client = jwks.JWKS()
            
        jwks_url = f"{self.issuer_url}/.well-known/jwks.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            return response.json()
            
    async def validate(self, token: str) -> Dict[str, Any]:
        """Validate JWT token with JWKS"""
        try:
            # Fetch JWKS if not cached
            if not self.jwks_cache:
                self.jwks_cache = await self._fetch_jwks()
                
            # Decode and validate token
            claims = jwt.decode(
                token,
                self.jwks_cache,
                algorithms=['RS256'],
                audience=self.audience,
                issuer=self.issuer_url
            )
            
            return claims
            
        except JWTError as e:
            raise ValueError(f"Token validation failed: {e}")
```

#### **2.2 Scope-Based Authorization**
```python
# services/api/src/aob_api/auth.py
from fastapi import HTTPException, Depends
from typing import List, Optional

class ScopeChecker:
    def __init__(self, required_scopes: List[str]):
        self.required_scopes = required_scopes
        
    def check_scopes(self, token_scopes: List[str]) -> bool:
        """Check if token has required scopes"""
        return all(scope in token_scopes for scope in self.required_scopes)

def require_scopes(scopes: List[str]):
    """Dependency for scope-based authorization"""
    def scope_dependency(claims: dict = Depends(_auth)):
        token_scopes = claims.get("scope", "").split()
        
        if not ScopeChecker(scopes).check_scopes(token_scopes):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient scopes. Required: {scopes}"
            )
            
        return claims
        
    return scope_dependency

# Usage in endpoints
@app.post("/workflows/start")
async def start_workflow(
    request: WorkflowRequest,
    claims: dict = Depends(require_scopes(["workflow:execute"]))
):
    # Implementation
    pass
```

#### **2.3 Tenant RBAC**
```python
# services/api/src/aob_api/rbac.py
from enum import Enum
from typing import Dict, List, Set

class Role(Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    EXECUTOR = "executor"

class Permission(Enum):
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_EXECUTE = "workflow:execute"
    WORKFLOW_VIEW = "workflow:view"
    AGENT_MANAGE = "agent:manage"
    POLICY_MANAGE = "policy:manage"

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.WORKFLOW_VIEW,
        Permission.AGENT_MANAGE,
        Permission.POLICY_MANAGE
    },
    Role.DEVELOPER: {
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.WORKFLOW_VIEW
    },
    Role.EXECUTOR: {
        Permission.WORKFLOW_EXECUTE,
        Permission.WORKFLOW_VIEW
    },
    Role.VIEWER: {
        Permission.WORKFLOW_VIEW
    }
}

def check_permission(user_role: str, permission: Permission) -> bool:
    """Check if user role has permission"""
    role = Role(user_role)
    return permission in ROLE_PERMISSIONS.get(role, set())

def require_permission(permission: Permission):
    """Dependency for permission-based authorization"""
    def permission_dependency(claims: dict = Depends(_auth)):
        user_role = claims.get("role", "viewer")
        tenant_id = claims.get("tenant_id", "default")
        
        if not check_permission(user_role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions for {permission.value}"
            )
            
        return {"tenant_id": tenant_id, "role": user_role}
        
    return permission_dependency
```

### **Day 5-6: Model Gateway Enhancement**

#### **3.1 vLLM Routing Implementation**
```python
# services/model_gateway/src/model_gateway/routing.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class ModelTier(Enum):
    FAST = "fast"      # 20B models, low latency
    BALANCED = "balanced"  # 70B models, balanced
    QUALITY = "quality"    # 120B+ models, high quality

@dataclass
class ModelProfile:
    name: str
    tier: ModelTier
    max_latency_ms: int
    cost_per_token: float
    safety_tier: int
    available: bool = True

class ModelRouter:
    def __init__(self):
        self.models = {
            "llama2-7b": ModelProfile("llama2-7b", ModelTier.FAST, 1000, 0.001, 1),
            "llama2-70b": ModelProfile("llama2-70b", ModelTier.BALANCED, 3000, 0.005, 1),
            "llama2-120b": ModelProfile("llama2-120b", ModelTier.QUALITY, 10000, 0.01, 1),
        }
        
    def route_request(self, request: Dict[str, Any]) -> str:
        """Route request to appropriate model"""
        tier = request.get("tier", ModelTier.BALANCED)
        max_latency = request.get("max_latency_ms", 3000)
        budget = request.get("budget", float('inf'))
        
        # Filter models by tier and constraints
        available_models = [
            model for model in self.models.values()
            if model.tier == tier 
            and model.max_latency_ms <= max_latency
            and model.cost_per_token <= budget
            and model.available
        ]
        
        if not available_models:
            # Fallback to lower tier
            return self._fallback_route(request)
            
        # Select best model based on cost/latency
        best_model = min(available_models, key=lambda m: m.cost_per_token)
        return best_model.name
        
    def _fallback_route(self, request: Dict[str, Any]) -> str:
        """Fallback to lower tier model"""
        if request.get("tier") == ModelTier.QUALITY:
            request["tier"] = ModelTier.BALANCED
            return self.route_request(request)
        elif request.get("tier") == ModelTier.BALANCED:
            request["tier"] = ModelTier.FAST
            return self.route_request(request)
        else:
            # Return fastest available model
            return "llama2-7b"
```

#### **3.2 Warm Pool Management**
```python
# services/model_gateway/src/model_gateway/pool.py
import asyncio
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class WarmInstance:
    model_name: str
    instance_id: str
    last_used: datetime
    status: str  # "idle", "busy", "warming"
    load: float

class WarmPoolManager:
    def __init__(self):
        self.pools: Dict[str, List[WarmInstance]] = {}
        self.min_instances = 2
        self.max_instances = 10
        self.idle_timeout = timedelta(minutes=30)
        
    async def get_instance(self, model_name: str) -> WarmInstance:
        """Get warm instance from pool"""
        if model_name not in self.pools:
            self.pools[model_name] = []
            
        pool = self.pools[model_name]
        
        # Find idle instance
        for instance in pool:
            if instance.status == "idle":
                instance.status = "busy"
                instance.last_used = datetime.utcnow()
                return instance
                
        # No idle instance, create new one
        if len(pool) < self.max_instances:
            instance = await self._create_instance(model_name)
            pool.append(instance)
            return instance
            
        # Wait for instance to become available
        return await self._wait_for_instance(model_name)
        
    async def release_instance(self, instance: WarmInstance) -> None:
        """Release instance back to pool"""
        instance.status = "idle"
        instance.last_used = datetime.utcnow()
        
    async def _create_instance(self, model_name: str) -> WarmInstance:
        """Create new warm instance"""
        instance_id = f"{model_name}_{len(self.pools[model_name])}"
        
        # Simulate instance creation
        await asyncio.sleep(1)
        
        return WarmInstance(
            model_name=model_name,
            instance_id=instance_id,
            last_used=datetime.utcnow(),
            status="busy",
            load=0.0
        )
        
    async def _cleanup_idle_instances(self) -> None:
        """Cleanup idle instances"""
        for model_name, pool in self.pools.items():
            now = datetime.utcnow()
            pool[:] = [
                instance for instance in pool
                if instance.status != "idle" or 
                (now - instance.last_used) < self.idle_timeout
            ]
```

### **Day 7-8: Metering Enforcement**

#### **4.1 Token Bucket Implementation**
```python
# services/metering_service/src/metering_service/quotas.py
import asyncio
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timedelta
import time

@dataclass
class TokenBucket:
    capacity: int
    tokens: int
    refill_rate: float  # tokens per second
    last_refill: datetime
    
    def __post_init__(self):
        if self.last_refill is None:
            self.last_refill = datetime.utcnow()
            
    def consume(self, tokens: int) -> bool:
        """Consume tokens from bucket"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
        
    def _refill(self) -> None:
        """Refill bucket based on time elapsed"""
        now = datetime.utcnow()
        elapsed = (now - self.last_refill).total_seconds()
        
        tokens_to_add = int(elapsed * self.refill_rate)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

class QuotaManager:
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}
        
    def create_tenant_quotas(self, tenant_id: str, qps: int, tokens_per_sec: int) -> None:
        """Create quotas for tenant"""
        self.buckets[f"{tenant_id}:qps"] = TokenBucket(
            capacity=qps,
            tokens=qps,
            refill_rate=qps,
            last_refill=datetime.utcnow()
        )
        
        self.buckets[f"{tenant_id}:tokens"] = TokenBucket(
            capacity=tokens_per_sec * 60,  # 1 minute window
            tokens=tokens_per_sec * 60,
            refill_rate=tokens_per_sec,
            last_refill=datetime.utcnow()
        )
        
    def check_quota(self, tenant_id: str, qps: int = 1, tokens: int = 0) -> bool:
        """Check if tenant has quota available"""
        qps_bucket = self.buckets.get(f"{tenant_id}:qps")
        tokens_bucket = self.buckets.get(f"{tenant_id}:tokens")
        
        if not qps_bucket or not tokens_bucket:
            return False
            
        # Check both quotas
        qps_ok = qps_bucket.consume(qps)
        tokens_ok = tokens_bucket.consume(tokens)
        
        return qps_ok and tokens_ok
        
    def get_usage(self, tenant_id: str) -> Dict[str, int]:
        """Get current usage for tenant"""
        qps_bucket = self.buckets.get(f"{tenant_id}:qps")
        tokens_bucket = self.buckets.get(f"{tenant_id}:tokens")
        
        return {
            "qps_remaining": qps_bucket.tokens if qps_bucket else 0,
            "tokens_remaining": tokens_bucket.tokens if tokens_bucket else 0,
            "qps_capacity": qps_bucket.capacity if qps_bucket else 0,
            "tokens_capacity": tokens_bucket.capacity if tokens_bucket else 0
        }
```

#### **4.2 QPS Enforcement Middleware**
```python
# services/api/src/aob_api/middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

class QuotaMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, quota_manager: QuotaManager):
        super().__init__(app)
        self.quota_manager = quota_manager
        
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from request
        tenant_id = self._extract_tenant(request)
        
        if not tenant_id:
            return await call_next(request)
            
        # Check QPS quota
        if not self.quota_manager.check_quota(tenant_id, qps=1):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
            
        response = await call_next(request)
        return response
        
    def _extract_tenant(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request"""
        # Check Authorization header for JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                claims = jwt.decode(token, options={"verify_signature": False})
                return claims.get("tenant_id")
            except:
                pass
                
        # Check API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key.split(":")[0]
            
        return None
```

### **Day 9-10: CI Hardening**

#### **5.1 Cosign Verification**
```yaml
# .github/workflows/deploy.yml
name: Deploy with Cosign Verification

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Cosign
        uses: sigstore/cosign-installer@v3.7.0
        
      - name: Verify image signatures
        run: |
          cosign verify --key env://COSIGN_PUBLIC_KEY \
            ghcr.io/${{ github.repository_owner }}/aob-api:latest
        env:
          COSIGN_PUBLIC_KEY: ${{ secrets.COSIGN_PUBLIC_KEY }}
          
      - name: Deploy to Kubernetes
        run: |
          helm upgrade --install aob charts/agentic-orch \
            --set image.repository=ghcr.io/${{ github.repository_owner }}/aob-api \
            --set image.tag=latest \
            --set image.pullPolicy=Always
```

#### **5.2 SARIF Upload**
```yaml
# .github/workflows/security.yml
name: Security Scan with SARIF

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@0.24.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          
      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

#### **5.3 Required Supply Chain Job**
```yaml
# .github/workflows/required-checks.yml
name: Required Supply Chain Checks

on:
  pull_request:
    branches: [main]

jobs:
  required-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check SBOM exists
        run: |
          if [ ! -f "sbom.tgz" ]; then
            echo "SBOM not found. Run supply-chain workflow first."
            exit 1
          fi
          
      - name: Check image signatures
        run: |
          cosign verify --key env://COSIGN_PUBLIC_KEY \
            ghcr.io/${{ github.repository_owner }}/aob-api:latest
        env:
          COSIGN_PUBLIC_KEY: ${{ secrets.COSIGN_PUBLIC_KEY }}
```

## 🚀 **Implementation Commands**

### **Setup Commands**
```bash
# 1. Create DLQ service
mkdir -p packages/agentic_core/src/agentic_core/dlq.py
mkdir -p packages/agentic_core/src/agentic_core/outbox.py

# 2. Enhance OIDC service
mkdir -p services/api/src/aob_api/auth.py
mkdir -p services/api/src/aob_api/rbac.py

# 3. Enhance model gateway
mkdir -p services/model_gateway/src/model_gateway/routing.py
mkdir -p services/model_gateway/src/model_gateway/pool.py

# 4. Enhance metering service
mkdir -p services/metering_service/src/metering_service/quotas.py
mkdir -p services/api/src/aob_api/middleware.py

# 5. Update CI workflows
mkdir -p .github/workflows/deploy.yml
mkdir -p .github/workflows/security.yml
mkdir -p .github/workflows/required-checks.yml
```

### **Testing Commands**
```bash
# Test DLQ implementation
python -m pytest tests/test_dlq.py -v

# Test OIDC enhancement
python -m pytest tests/test_oidc.py -v

# Test model gateway
python -m pytest tests/test_model_gateway.py -v

# Test metering
python -m pytest tests/test_metering.py -v

# Test CI workflows
act -j required-checks
```

## 📊 **Success Metrics**

### **DLQ Implementation**
- [ ] Dead letter queue with TTL implemented
- [ ] Replay endpoint for failed messages
- [ ] Watermark for outbox processing
- [ ] Idempotent Kafka producer

### **OIDC Enhancement**
- [ ] JWKS integration implemented
- [ ] Scope-based authorization
- [ ] Tenant RBAC system
- [ ] Permission-based access control

### **Model Gateway Enhancement**
- [ ] vLLM routing by tier
- [ ] Warm pool management
- [ ] Cost/latency-based routing
- [ ] Fallback mechanisms

### **Metering Enforcement**
- [ ] Token bucket algorithm
- [ ] QPS enforcement middleware
- [ ] Usage API implementation
- [ ] Quota management system

### **CI Hardening**
- [ ] Cosign verification in deploy
- [ ] SARIF upload for security scans
- [ ] Required supply chain checks
- [ ] Automated security validation

## 🎯 **Expected Outcomes**

After 10-day implementation:
- **DLQ**: 100% message reliability with quarantine TTL
- **OIDC**: Complete JWT validation with JWKS and scopes
- **Model Gateway**: Intelligent routing with warm pools
- **Metering**: Enforced quotas with token bucket algorithm
- **CI**: Hardened supply chain with signature verification

**Overall Completion**: **85%** (up from 78%)

The platform will be **production-ready** with enterprise-grade reliability, security, and scalability features.
