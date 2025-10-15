
## Agentic Orchestration Builder — Monorepo

Reimagined n8n for agentic, event‑driven workflows. Supports deterministic DAGs and adaptive agent behavior with policy‑gated edges, human‑in‑the‑loop, replayable state, and observability.

## Access the service (TL;DR)
```bash
# Option A: docker-compose (recommended)
cd docker && docker compose up --build
# API: http://localhost:8000, OPA: http://localhost:8181, Audit: http://localhost:8085

# Option B: single API container
docker build -f docker/Dockerfile.api -t aob-api .
docker run -p 8000:8000 aob-api
# API: http://localhost:8000

# Option C: Helm (Kubernetes)
helm install aob charts/agentic-orch -n aob --create-namespace
kubectl -n aob port-forward deploy/agentic-orch 8000:8000
# API: http://localhost:8000
```

Endpoints (HATEOAS)
- GET `/` → links
- POST `/workflows/compile` → upload YAML
- POST `/workflows/start` → start
- POST `/workflows/resume` → resume with approval
- GET `/workflows/{cid}/events` → event log
- Stubs: `POST /agents`, `POST /invocations`, `POST /sessions`

### Tech stack
- **Language**: Python 3.11
- **API**: FastAPI
- **Eventing**: Kafka (dev: in‑memory queue also available)
- **State**: Postgres (dev: in‑memory store also available)
- **Policy**: OPA (Open Policy Agent)
- **Observability**: OpenTelemetry (OTLP/HTTP)
- **Containers/Orchestration**: Docker, Helm, Kubernetes

### Enterprise 3‑layer architecture
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ③ GENERAL WORKFLOW ENGINE (Graph of Agents)                                 │
│  DAG/graph compiler • SLA/cost-aware routing • HITL gates • decision fusion  │
│  OPA policy on edges • lineage/replay • actuation adapters (tickets/APIs)    │
└──────────────▲───────────────────────────────────────────────────────────────┘
               │  (typed results from agents + tool calls + RAG bundles)
┌──────────────┴───────────────────────────────────────────────────────────────┐
│  ② AGENTS LAYER — Processing • Decision • Interaction units                   │
│  Retrieval/parsing/sim • rules/optimizers/MCDA • chat/UX/HITL • agent mesh   │
│  Standard tool protocol (MCP) • stateful LangGraph-style orchestration        │
└──────────────▲───────────────────────────────────────────────────────────────┘
               │  (APIs: data/models/tools/policy/obs; zero-trust by default)
┌──────────────┴───────────────────────────────────────────────────────────────┐
│  ① CAPABILITIES LAYER (Foundational primitives)                               │
│  Streams/CDC/ETL • Hybrid knowledge fabric (graph + vector + keyword + SQL)   │
│  Model gateway (vLLM/hosted) • Tool registry (MCP servers) • OPA • OTEL       │
│  Platform: K8s + mesh • multi-tenant • GitOps • HA/DR • quotas/FinOps         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3‑plane AaaS reference architecture
```
┌────────────────────────────── CONTROL PLANE ────────────────────────────────┐
│ Agent Registry | Versioning | Catalog | Tenancy+RBAC | Policy Mgmt (OPA)   │
│ Eval/Promote   | Pricing/SKUs | API Keys/OAuth | Metering/Billing          │
└───────────────▲─────────────────────────────────────────────────────────────┘
                │ (AgentSpec, PolicyBundle, Tool contracts, Model profiles)
┌───────────────┴──────────────── DATA/POLICY PLANE ─────────────────────────┐
│ RAG bundle store | Vector+Graph+SQL fabric | Secrets/KMS | Audit/Lineage   │
│ Observability (OTel) | Artifact store (models/prompts/skills)              │
└───────────────▲─────────────────────────────────────────────────────────────┘
                │ (Invocation requests, events, tool calls, model IO)
┌───────────────┴──────────────── EXECUTION PLANE ───────────────────────────┐
│ API Gateway → Session Service → Execution Service (Runner Pool: pods/microVM)│
│ Model Gateway (vLLM/hosted) | Tool Gateway (MCP proxy) | HITL Console      │
│ DLQ/Retry/Kafka topics | Memory service | Snapshot/Replayer                │
└────────────────────────────────────────────────────────────────────────────┘
```

## Repository layout
- `packages/agentic_core` – engine, YAML compiler, policies, OTEL, audit
- `packages/agentic_adapters` – Kafka/Postgres adapters
- `services/api` – public API (HATEOAS), compiles/executes workflows
- `services/agent_registry` – AgentSpec CRUD (stub)
- `services/session_service` – sessions/HITL (stub)
- `services/metering_service` – usage counters (stub)
- `services/audit_service` – DecisionRecord ingest (stub)
- `services/worker` – background runners (placeholder)
- `charts/agentic-orch` – Helm chart
- `docker/` – Dockerfiles and docker‑compose
- `policies/` – OPA rego bundles
- `tests/` – sample tests
- `docs/pricing/` – SKU & pricing matrix (markdown + JSON)

## Core concepts
- **AgentSpec v1**: versioned agent package – graph, tools (MCP), policies, model profile, memory.
- **WorkflowSpec (YAML)**: declarative nodes and edges with `policies` on edges.
- **Events**: event‑sourced state (`events` table/stream) with replay.
- **Policy**: OPA decision `data.aob.allow` evaluated per edge.
- **DecisionRecord**: per‑node audit (inputs/outputs/policies/cost/latency).

### Sample WorkflowSpec YAML
```yaml
id: demo
nodes:
  - id: n1; kind: task; name: uppercase; expr: "ctx.bag"
  - id: n2; kind: agent; name: summarize; expr: "ctx.bag"
  - id: n3; kind: human; name: review; approval_key: "approval"
  - id: n4; kind: task; name: ship; expr: "ctx.bag"
edges:
  - from: n2; to: n3; policies: [require_human_for_risk_high]
```

### Sample Rego (policies/aob.rego)
```rego
package aob
default allow = true
deny_no_approval {
  input.edge.policies[_] == "require_human_for_risk_high"
  not input.ctx.bag.approval
}
allow { not deny_no_approval }
```

## Running locally (docker‑compose)
```bash
cd docker
docker compose up --build
```
Services:
- API: `http://localhost:8000`
- OPA: `http://localhost:8181`
- Audit: `http://localhost:8085`
- Agent Registry: `http://localhost:8081`
- Session Service: `http://localhost:8082`
- Metering: `http://localhost:8083`
- Postgres: `localhost:5432`
- Kafka: `localhost:9092`

### Try it
1) Compile a workflow
```bash
curl -s -X POST localhost:8000/workflows/compile -H 'content-type: application/json' \
  -d '{"yaml":"id: demo\nnodes:\n  - id: n1; kind: task; name: uppercase; expr: \"ctx.bag\"\n  - id: n2; kind: agent; name: summarize; expr: \"ctx.bag\"\n  - id: n3; kind: human; name: review; approval_key: \"approval\"\n  - id: n4; kind: task; name: ship; expr: \"ctx.bag\"\nedges:\n  - from: n2; to: n3; policies: [require_human_for_risk_high]\n"}'
```
2) Start without approval (expect policy gate or human wait)
```bash
curl -s -X POST localhost:8000/workflows/start -H 'content-type: application/json' \
  -d '{"workflow_id":"demo","text":"hello agentic","approval":false}'
```
3) Inspect events
```bash
curl -s localhost:8000/workflows/demo/events | jq
```
4) Approve and resume
```bash
curl -s -X POST localhost:8000/workflows/resume -H 'content-type: application/json' \
  -d '{"workflow_id":"demo","approval":true}'
```

## Observability (OpenTelemetry)
- OTEL spans are created per node execution.
- Default exporter: OTLP/HTTP. Configure via env vars:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_RESOURCE_ATTRIBUTES=service.name=agentic-core
```
Use any OTLP collector (e.g., OpenTelemetry Collector, Tempo, Jaeger via OTLP).

## Environment variables
- `OTEL_EXPORTER_OTLP_ENDPOINT` (default: none) – OTLP/HTTP endpoint, e.g. `http://localhost:4318`
- `AOB_OPA_URL` (optional) – override OPA base URL (default: `http://localhost:8181`)
- `AOB_AUDIT_ENDPOINT` (optional) – DecisionRecord sink (default: `http://localhost:8085/decisions`)
- `AOB_KAFKA_BOOTSTRAP` (optional) – Kafka bootstrap when using `KafkaBus`
- `AOB_POSTGRES_DSN` (optional) – Postgres DSN when using `PostgresEventStore`

## Policy evaluation (OPA)
- Engine posts to `POST /v1/data/aob/allow` with input:
```json
{
  "input": {
    "node": {"id":"n2","name":"summarize","kind":"AgentNode"},
    "ctx": {"bag": {"approval": false}},
    "policies": ["require_human_for_risk_high"],
    "edge": {"from":"n2","to":"n3","policies":["require_human_for_risk_high"]}
  }
}
```
Return `true`/`{"allow": true}` to admit, otherwise the engine emits a `policy.denied` event.

## Public API (HATEOAS snippets)
- `GET /` → links
- `POST /workflows/compile` → load YAML
- `POST /workflows/start` → start demo workflow
- `POST /workflows/resume` → resume with approval
- `GET /workflows/{cid}/events` → event log
- AaaS stubs:
  - `POST /agents` { spec }
  - `POST /invocations` { agent_id, version, input }
  - `POST /sessions` { agent_id, input }

## Helm (Kubernetes)
```bash
helm install aob charts/agentic-orch -n aob --create-namespace \
  --set image.repository=aob-api --set image.tag=latest
```
Values (`charts/agentic-orch/values.yaml`) include optional sidecars:
- `agentRegistry.*`, `sessionService.*`, `meteringService.*`, `auditService.*`

## Pricing (reference)
- See `docs/pricing/sku_matrix.md` and `docs/pricing/sku_matrix.json` for packaging, meters, and example plans (Starter/Pro/Enterprise). Tailor to your deployment model.

## CI/CD and deployments
- GitHub Container Registry (GHCR) builds
  - On push to `main`, images are built and pushed to `ghcr.io/<OWNER>/...`
  - Workflows: `.github/workflows/build-images.yml`, `.github/workflows/publish-helm.yml`
- Helm chart (OCI)
  - Chart packaged and pushed to `oci://ghcr.io/<OWNER>`
  - Argo CD can pull the OCI chart directly
- Argo CD multi-cluster
  - `deploy/argocd/applicationset.yaml` defines per-cluster app with Helm values
  - Set `GITHUB_OWNER` env in Argo CD controller for OCI repo path
- Cloud overlays
  - `deploy/kustomize/overlays/{aws,azure,gcp}/values.yaml` provide LB annotations

### Required GitHub secrets (recommend OIDC where possible)
- For GHCR: none required (uses `GITHUB_TOKEN`), ensure Packages: write permission enabled
- For cluster deploys via GitHub Actions to cloud (optional):
  - AWS: `AWS_ROLE_TO_ASSUME`, `AWS_REGION` (use OIDC; configure trust for `repo:<owner>/<repo>:ref:refs/heads/main`)
  - Azure: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (federated credentials)
  - GCP: `WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` (OIDC), or `GCP_SA_KEY` as fallback

### Argo CD setup
1) Install Argo CD in each cluster
2) Create a repo credential for GHCR OCI if private
3) Apply `deploy/argocd/applicationset.yaml` (tweak cluster/namespace/owner)
4) Sync apps; verify API exposed

## Extending
- Add real Postgres/Kafka by switching to `PostgresEventStore` and `KafkaBus` in your API init.
- Implement `tool-gateway` and `model-gateway` services.
- Harden OPA (bundles, signature verification, fine‑grained policies).

## Troubleshooting
- API not starting: ensure ports `8000/8081/8082/8083/8085/8181` are free.
- OPA decisions always allow: confirm `policies/aob.rego` is mounted and OPA at `:8181`.
- No spans: set `OTEL_EXPORTER_OTLP_ENDPOINT` to a running collector.
- Events empty: you may be using in‑memory store; switch to Postgres adapter for persistence.
