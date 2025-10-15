## Agentic Orchestration Builder — SKU & Pricing Matrix (Reference)

This is a reference SKU set for packaging the platform. Prices are placeholders; tailor per deployment (SaaS, Dedicated VPC, On‑prem).

### Definitions
- Tenant: logical customer/account, isolated via namespaces/keys.
- Invocation: a single agent run (stateless) or one session step (stateful).
- Decision Step: execution of a graph node (task/agent/human checkpoint).

### SKUs

| SKU | What’s included | Meters | Notes |
| --- | --- | --- | --- |
| Platform Core | Control plane, API, session service, registry, basic policy, audit UI | tenants, peak QPS, storage GB | Base subscription; throughput cap per tier |
| Execution Tier – Serverless | Per‑invocation compute on shared runner pools | invocations, compute_sec | Cold starts possible; prepaid bundles or pay‑go |
| Execution Tier – Reserved | Dedicated runners (pods/microVMs) | reserved_vCPU, reserved_RAM, uptime | SLAs 99.95–99.99; surge overage billed as serverless |
| Model Pack – OSS | vLLM backed OSS models | tokens_in, tokens_out | Per‑token blended; optional GPU reservation add‑on |
| Model Pack – Premium | Hosted proprietary models | provider_bill_through | Pass‑through + margin; or bring‑your‑own contracts |
| Tool Pack – Connectors | MCP servers for common systems | tool_calls | Tiered by connector families (ERP/CMMS/CRM/etc.) |
| Skill Pack – Vertical | Prebuilt graphs, prompts, ontologies | seats or per‑asset/site | Optional enablement/professional services |
| Policy Pack – Compliance | Residency/PII/redaction rules | policy_evals | Industry templates (HIPAA/GxP/SOX) |
| Observability Pack | Traces/logs retention, dashboards | gb_ingested, retention_days | SSO to customer SIEM optional |
| Ops SLA | Availability, support, DR | tier | 99.9/99.95/99.99; multi‑region add‑on |

### Primary meters (emitted per invocation/session)

- tokens_in, tokens_out
- tool_calls
- graph_steps (decision steps)
- compute_sec (CPU+GPU normalized)
- storage_gb (artifacts, event store)
- bundles_built (RAG precompiles)
- eval_runs (pre‑promotion/QA)

### Example packaging

- Starter: Platform Core + Serverless (10 QPS cap) + OSS Model Pack + 5 connectors
- Pro: Platform Core + Reserved (4 vCPU/16 GB) + OSS + Premium Model Pack + 15 connectors + Observability (30d)
- Enterprise: Platform Core + Reserved (custom) + Multi‑region + Premium + Policy/Skill Packs + 90d retention + 99.99% Ops SLA

### Billing notes

- Serverless invocations are rounded up to 100 ms, minimum 1 step.
- Tool errors (4xx from destination) are billable; platform errors (5xx) are not.
- Shadow runs and replays count against compute and model tokens but can be discounted by plan.

