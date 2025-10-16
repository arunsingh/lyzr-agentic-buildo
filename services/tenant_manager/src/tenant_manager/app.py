"""
Multi-tenant Database Schema Isolation

Per-tenant Postgres schemas with KMS integration and network policies.
"""

from __future__ import annotations
import asyncio
import json
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import asyncpg
import httpx
from cryptography.fernet import Fernet
import logging
import hashlib
import secrets

logger = logging.getLogger(__name__)


class TenantStatus(Enum):
    """Tenant status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class TenantConfig:
    """Tenant configuration"""
    tenant_id: str
    schema_name: str
    encryption_key: bytes
    status: TenantStatus
    created_at: str
    metadata: Dict[str, Any]
    quotas: Dict[str, int]
    policies: List[str]


class TenantManager:
    """Multi-tenant database manager"""
    
    def __init__(self, master_dsn: str):
        self.master_dsn = master_dsn
        self.tenants: Dict[str, TenantConfig] = {}
        self.connections: Dict[str, asyncpg.Connection] = {}
        self._master_conn: Optional[asyncpg.Connection] = None
        
        # KMS integration (placeholder)
        self.kms_endpoint = os.getenv("AOB_KMS_ENDPOINT", "http://localhost:9001")
        
        # Initialize master connection
        asyncio.create_task(self._init_master_connection())
    
    async def _init_master_connection(self):
        """Initialize master database connection"""
        try:
            self._master_conn = await asyncpg.connect(self.master_dsn)
            await self._create_tenant_management_tables()
            await self._load_tenant_configs()
        except Exception as e:
            logger.error(f"Failed to initialize master connection: {e}")
    
    async def _create_tenant_management_tables(self):
        """Create tenant management tables"""
        await self._master_conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id VARCHAR(255) PRIMARY KEY,
                schema_name VARCHAR(255) UNIQUE NOT NULL,
                encryption_key_encrypted BYTEA NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW(),
                metadata JSONB DEFAULT '{}',
                quotas JSONB DEFAULT '{}',
                policies JSONB DEFAULT '[]'
            );
        """)
        
        await self._master_conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_schemas (
                schema_name VARCHAR(255) PRIMARY KEY,
                tenant_id VARCHAR(255) REFERENCES tenants(tenant_id),
                created_at TIMESTAMP DEFAULT NOW(),
                last_accessed TIMESTAMP DEFAULT NOW()
            );
        """)
    
    async def _load_tenant_configs(self):
        """Load tenant configurations from database"""
        rows = await self._master_conn.fetch("SELECT * FROM tenants WHERE status != 'deleted'")
        
        for row in rows:
            # Decrypt encryption key (placeholder)
            encryption_key = self._decrypt_key(row['encryption_key_encrypted'])
            
            tenant_config = TenantConfig(
                tenant_id=row['tenant_id'],
                schema_name=row['schema_name'],
                encryption_key=encryption_key,
                status=TenantStatus(row['status']),
                created_at=str(row['created_at']),
                metadata=row['metadata'] or {},
                quotas=row['quotas'] or {},
                policies=row['policies'] or []
            )
            
            self.tenants[row['tenant_id']] = tenant_config
    
    def _encrypt_key(self, key: bytes) -> bytes:
        """Encrypt encryption key (placeholder implementation)"""
        # In production, this would use proper KMS
        master_key = os.getenv("AOB_MASTER_KEY", Fernet.generate_key())
        fernet = Fernet(master_key)
        return fernet.encrypt(key)
    
    def _decrypt_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt encryption key (placeholder implementation)"""
        # In production, this would use proper KMS
        master_key = os.getenv("AOB_MASTER_KEY", Fernet.generate_key())
        fernet = Fernet(master_key)
        return fernet.decrypt(encrypted_key)
    
    async def create_tenant(
        self, 
        tenant_id: str, 
        metadata: Dict[str, Any] = None,
        quotas: Dict[str, int] = None,
        policies: List[str] = None
    ) -> TenantConfig:
        """Create a new tenant with isolated schema"""
        
        if tenant_id in self.tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")
        
        # Generate schema name
        schema_name = f"tenant_{tenant_id.replace('-', '_')}"
        
        # Generate encryption key
        encryption_key = Fernet.generate_key()
        
        # Create tenant config
        tenant_config = TenantConfig(
            tenant_id=tenant_id,
            schema_name=schema_name,
            encryption_key=encryption_key,
            status=TenantStatus.ACTIVE,
            created_at=str(asyncio.get_event_loop().time()),
            metadata=metadata or {},
            quotas=quotas or {},
            policies=policies or []
        )
        
        # Create schema in database
        await self._create_tenant_schema(tenant_config)
        
        # Store tenant config
        encrypted_key = self._encrypt_key(encryption_key)
        await self._master_conn.execute("""
            INSERT INTO tenants (tenant_id, schema_name, encryption_key_encrypted, metadata, quotas, policies)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, tenant_id, schema_name, encrypted_key, json.dumps(metadata or {}), json.dumps(quotas or {}), json.dumps(policies or []))
        
        await self._master_conn.execute("""
            INSERT INTO tenant_schemas (schema_name, tenant_id)
            VALUES ($1, $2)
        """, schema_name, tenant_id)
        
        self.tenants[tenant_id] = tenant_config
        return tenant_config
    
    async def _create_tenant_schema(self, tenant_config: TenantConfig):
        """Create isolated schema for tenant"""
        schema_name = tenant_config.schema_name
        
        # Create schema
        await self._master_conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        
        # Create tenant-specific tables
        await self._master_conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.events (
                id BIGSERIAL PRIMARY KEY,
                correlation_id VARCHAR(255) NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                payload JSONB NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                causation_id VARCHAR(255),
                idempotency_key VARCHAR(255)
            );
        """)
        
        await self._master_conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.snapshots (
                id BIGSERIAL PRIMARY KEY,
                correlation_id VARCHAR(255) NOT NULL,
                snapshot_id VARCHAR(255) UNIQUE NOT NULL,
                state JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                checksum VARCHAR(64)
            );
        """)
        
        await self._master_conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.sessions (
                id BIGSERIAL PRIMARY KEY,
                session_id VARCHAR(255) UNIQUE NOT NULL,
                correlation_id VARCHAR(255),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW(),
                last_accessed TIMESTAMP DEFAULT NOW(),
                metadata JSONB DEFAULT '{{}}'
            );
        """)
        
        await self._master_conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.outbox (
                id BIGSERIAL PRIMARY KEY,
                event_id BIGINT REFERENCES {schema_name}.events(id),
                topic VARCHAR(255) NOT NULL,
                payload JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                delivered_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            );
        """)
        
        # Create indexes
        await self._master_conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_events_correlation 
            ON {schema_name}.events(correlation_id);
        """)
        
        await self._master_conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_snapshots_correlation 
            ON {schema_name}.snapshots(correlation_id);
        """)
        
        await self._master_conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{schema_name}_outbox_undelivered 
            ON {schema_name}.outbox(delivered_at) WHERE delivered_at IS NULL;
        """)
        
        # Grant permissions (placeholder - would be more sophisticated in production)
        await self._master_conn.execute(f"""
            GRANT USAGE ON SCHEMA {schema_name} TO aob_user;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema_name} TO aob_user;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema_name} TO aob_user;
        """)
    
    async def get_tenant_connection(self, tenant_id: str) -> asyncpg.Connection:
        """Get database connection for specific tenant"""
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant_config = self.tenants[tenant_id]
        
        if tenant_id in self.connections:
            return self.connections[tenant_id]
        
        # Create tenant-specific connection
        tenant_dsn = self.master_dsn.replace('/aob', f'/aob?options=-csearch_path={tenant_config.schema_name}')
        conn = await asyncpg.connect(tenant_dsn)
        
        # Set search path to tenant schema
        await conn.execute(f"SET search_path TO {tenant_config.schema_name}")
        
        self.connections[tenant_id] = conn
        return conn
    
    async def encrypt_tenant_data(self, tenant_id: str, data: bytes) -> bytes:
        """Encrypt data using tenant-specific key"""
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant_config = self.tenants[tenant_id]
        fernet = Fernet(tenant_config.encryption_key)
        return fernet.encrypt(data)
    
    async def decrypt_tenant_data(self, tenant_id: str, encrypted_data: bytes) -> bytes:
        """Decrypt data using tenant-specific key"""
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant_config = self.tenants[tenant_id]
        fernet = Fernet(tenant_config.encryption_key)
        return fernet.decrypt(encrypted_data)
    
    async def check_tenant_quota(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        """Check if tenant has quota for resource"""
        if tenant_id not in self.tenants:
            return False
        
        tenant_config = self.tenants[tenant_id]
        
        if resource not in tenant_config.quotas:
            return True  # No quota limit
        
        # Check current usage (placeholder - would query actual usage)
        current_usage = await self._get_tenant_usage(tenant_id, resource)
        quota_limit = tenant_config.quotas[resource]
        
        return current_usage + amount <= quota_limit
    
    async def _get_tenant_usage(self, tenant_id: str, resource: str) -> int:
        """Get current usage for tenant resource (placeholder)"""
        # In production, this would query actual usage metrics
        return 0
    
    async def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend tenant access"""
        if tenant_id not in self.tenants:
            return False
        
        tenant_config = self.tenants[tenant_id]
        tenant_config.status = TenantStatus.SUSPENDED
        
        await self._master_conn.execute("""
            UPDATE tenants SET status = 'suspended' WHERE tenant_id = $1
        """, tenant_id)
        
        return True
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete tenant and all data"""
        if tenant_id not in self.tenants:
            return False
        
        tenant_config = self.tenants[tenant_id]
        
        # Mark as deleted
        tenant_config.status = TenantStatus.DELETED
        
        await self._master_conn.execute("""
            UPDATE tenants SET status = 'deleted' WHERE tenant_id = $1
        """, tenant_id)
        
        # Close connection
        if tenant_id in self.connections:
            await self.connections[tenant_id].close()
            del self.connections[tenant_id]
        
        # Remove from memory
        del self.tenants[tenant_id]
        
        return True
    
    async def get_tenant_stats(self) -> Dict[str, Any]:
        """Get tenant statistics"""
        stats = {
            "total_tenants": len(self.tenants),
            "active_tenants": sum(1 for t in self.tenants.values() if t.status == TenantStatus.ACTIVE),
            "suspended_tenants": sum(1 for t in self.tenants.values() if t.status == TenantStatus.SUSPENDED),
            "tenants_by_policy": {},
            "total_schemas": len(set(t.schema_name for t in self.tenants.values()))
        }
        
        # Group by policies
        for tenant in self.tenants.values():
            for policy in tenant.policies:
                if policy not in stats["tenants_by_policy"]:
                    stats["tenants_by_policy"][policy] = 0
                stats["tenants_by_policy"][policy] += 1
        
        return stats
    
    async def close(self):
        """Close all connections"""
        for conn in self.connections.values():
            await conn.close()
        
        if self._master_conn:
            await self._master_conn.close()


# Global instance
tenant_manager = TenantManager(os.getenv("AOB_POSTGRES_DSN", "postgres://postgres:postgres@localhost:55432/aob"))


# FastAPI integration
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Multi-tenant Database Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_tenant_id(x_tenant_id: str = Header(None)) -> str:
    """Extract tenant ID from header"""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")
    return x_tenant_id


@app.post("/tenants")
async def create_tenant(
    tenant_id: str,
    metadata: Dict[str, Any] = None,
    quotas: Dict[str, int] = None,
    policies: List[str] = None
):
    """Create a new tenant"""
    try:
        tenant_config = await tenant_manager.create_tenant(
            tenant_id, metadata, quotas, policies
        )
        return {
            "tenant_id": tenant_config.tenant_id,
            "schema_name": tenant_config.schema_name,
            "status": tenant_config.status.value,
            "created_at": tenant_config.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant information"""
    if tenant_id not in tenant_manager.tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_config = tenant_manager.tenants[tenant_id]
    return {
        "tenant_id": tenant_config.tenant_id,
        "schema_name": tenant_config.schema_name,
        "status": tenant_config.status.value,
        "created_at": tenant_config.created_at,
        "metadata": tenant_config.metadata,
        "quotas": tenant_config.quotas,
        "policies": tenant_config.policies
    }


@app.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str):
    """Suspend tenant"""
    success = await tenant_manager.suspend_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"status": "suspended"}


@app.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str):
    """Delete tenant"""
    success = await tenant_manager.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"status": "deleted"}


@app.get("/tenants/stats")
async def get_tenant_stats():
    """Get tenant statistics"""
    return await tenant_manager.get_tenant_stats()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "tenants": len(tenant_manager.tenants)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8089)
