# OIDC Authentication Setup Guide

This guide covers setting up OIDC authentication with Keycloak for the Agentic Orchestration Builder (AOB) platform.

## Overview

The AOB platform supports OIDC authentication using Keycloak as the identity provider. This provides:
- JWT token validation with JWKS
- Multi-tenant support via realm/tenant mapping
- Scope-based authorization
- Fallback to API key authentication for local development

## Dependencies

### Python Packages
The API service requires these additional packages for OIDC support:

```toml
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0", 
  "pydantic>=2.8.0",
  "pyyaml>=6.0.1",
  "python-jose[cryptography]>=3.3.0",  # JWT validation and JWKS handling
  "httpx>=0.27.0",                     # Async HTTP client for JWKS fetching
  "agentic-core==0.1.0"
]
```

### Keycloak Server
- Version: 26.0.2 (or compatible)
- Docker image: `quay.io/keycloak/keycloak:26.0.2`
- Default admin: `admin/admin`
- Default port: `8080`

## Environment Configuration

### Required Environment Variables

```bash
# OIDC Configuration
OIDC_ISSUER_URL=http://localhost:8080/realms/demo
OIDC_AUDIENCE=aob-api
OIDC_REQUIRED_SCOPES=  # Space-delimited scopes (optional)

# OpenTelemetry (for distributed tracing)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_RESOURCE_ATTRIBUTES=service.name=agentic-core

# Other AOB Configuration
AOB_OPA_URL=http://localhost:8181
AOB_AUDIT_ENDPOINT=http://localhost:8085/decisions
AOB_REDIS_URL=redis://localhost:6379/0
```

## Keycloak Setup

### 1. Start Keycloak
```bash
cd docker
docker compose up keycloak
```

### 2. Access Admin Console
- URL: `http://localhost:8080`
- Username: `admin`
- Password: `admin`

### 3. Create Realm
1. Click "Create realm"
2. Name: `demo`
3. Click "Create"

### 4. Create Client
1. Go to "Clients" → "Create client"
2. Client ID: `aob-api`
3. Client type: `OpenID Connect`
4. Valid redirect URIs: `http://localhost:8000/*`
5. Click "Save"

### 5. Configure Client Settings
1. Access Type: `public`
2. Standard Flow Enabled: `ON`
3. Direct Access Grants Enabled: `ON`
4. Service Accounts Enabled: `ON`
5. Authorization Enabled: `ON`
6. Click "Save"

### 6. Create User (Optional)
1. Go to "Users" → "Create new user"
2. Username: `testuser`
3. Email: `test@example.com`
4. Click "Save"
5. Go to "Credentials" tab → "Set password"
6. Password: `testpass`
7. Temporary: `OFF`
8. Click "Save"

## Token Usage

### Get Access Token
```bash
# Client credentials flow
TOKEN=$(curl -s -X POST \
  -H 'content-type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials&client_id=aob-api' \
  http://localhost:8080/realms/demo/protocol/openid-connect/token | jq -r .access_token)

echo $TOKEN
```

### Use Token in API Calls
```bash
# API call with Bearer token
curl -H "Authorization: Bearer $TOKEN" \
     -H 'content-type: application/json' \
     -d '{"workflow_id":"demo","text":"hello agentic","approval":false}' \
     localhost:8000/workflows/start
```

### Fallback API Key (Local Dev)
```bash
# Fallback to API key format: tenant:apikey
curl -H "X-API-Key: demo:local-dev-key" \
     -H 'content-type: application/json' \
     -d '{"workflow_id":"demo","text":"hello agentic","approval":false}' \
     localhost:8000/workflows/start
```

## Tenant Mapping

The platform derives tenant information from JWT claims in this order:

1. `tenant_id` claim (preferred)
2. `realm_access.realm` claim
3. Issuer realm (extracted from `iss` claim)

Example JWT payload:
```json
{
  "iss": "http://localhost:8080/realms/demo",
  "aud": "aob-api",
  "sub": "user-123",
  "tenant_id": "acme-corp",
  "scope": "read write",
  "exp": 1234567890
}
```

## Scope Enforcement

Configure required scopes via environment variable:
```bash
OIDC_REQUIRED_SCOPES="read write admin"
```

The platform will validate that the token contains all required scopes before allowing access.

## Distributed Tracing Integration

### Span Attributes
OIDC authentication adds these attributes to OpenTelemetry spans:

- `tenant.id`: Extracted tenant identifier
- `user.id`: JWT subject claim
- `auth.method`: "oidc" or "api-key"
- `auth.scopes`: Space-delimited scopes from token

### Trace Flow
```
HTTP Request → OIDC Validation → Tenant Extraction → Workflow Execution
     ↓              ↓                    ↓                    ↓
  API Span    Auth Span          Tenant Span          Node Spans
```

## Production Considerations

### Security
- Use HTTPS for all OIDC endpoints
- Rotate JWKS keys regularly
- Implement proper secret management
- Use short-lived tokens with refresh

### Performance
- Cache JWKS responses (default: 5 minutes)
- Use connection pooling for HTTP clients
- Consider Redis for token validation cache

### Monitoring
- Monitor JWKS fetch failures
- Track token validation errors
- Alert on authentication failures
- Monitor tenant mapping accuracy

## Troubleshooting

### Common Issues

1. **JWKS fetch fails**
   - Check network connectivity to Keycloak
   - Verify `OIDC_ISSUER_URL` is correct
   - Ensure Keycloak is running and accessible

2. **Token validation fails**
   - Verify token is not expired
   - Check audience matches `OIDC_AUDIENCE`
   - Ensure issuer matches `OIDC_ISSUER_URL`

3. **Scope validation fails**
   - Check `OIDC_REQUIRED_SCOPES` configuration
   - Verify token contains required scopes
   - Check client configuration in Keycloak

4. **Tenant mapping fails**
   - Verify JWT contains tenant claims
   - Check tenant extraction logic
   - Ensure fallback mechanisms work

### Debug Commands
```bash
# Test JWKS endpoint
curl http://localhost:8080/realms/demo/protocol/openid-connect/certs

# Decode JWT token (without verification)
echo $TOKEN | cut -d. -f2 | base64 -d | jq

# Test API endpoint
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8000/
```

## Integration with Other Services

### Tool Gateway
The tool gateway service also supports OIDC authentication:
```python
# In tool_gateway/app.py
from aob_api.oidc import OIDC

oidc = OIDC()

async def validate_token(token: str) -> str:
    claims = await oidc.validate(token)
    return OIDC.tenant_from_claims(claims)
```

### Model Gateway
Similar OIDC integration can be added to the model gateway for consistent authentication across all services.

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OpenTelemetry Authentication](https://opentelemetry.io/docs/specs/otel/trace/semantic_conventions/attributes/)
