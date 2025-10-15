# OpenTelemetry Distributed Tracing Guide

This guide covers OpenTelemetry (OTEL) integration and distributed tracing across the Agentic Orchestration Builder (AOB) platform.

## Overview

The AOB platform implements comprehensive distributed tracing using OpenTelemetry to provide observability across:
- API requests and responses
- Workflow execution and node processing
- Policy evaluation (OPA)
- Tool and model gateway calls
- Database operations
- Event publishing and consumption

## Architecture

### Trace Flow
```
Client Request → API Gateway → Workflow Engine → Node Execution → Policy Check → Tool/Model Call
     ↓              ↓              ↓              ↓              ↓              ↓
  HTTP Span    API Span      Engine Span    Node Span    Policy Span    Gateway Span
```

### Span Hierarchy
```
HTTP Request (Root)
├── Workflow Execution
│   ├── Node Execution (n1)
│   │   ├── Policy Evaluation
│   │   └── Tool Call
│   ├── Node Execution (n2)
│   │   ├── Policy Evaluation
│   │   └── Model Call
│   └── Human Approval
└── Event Publishing
```

## Configuration

### Environment Variables
```bash
# OTLP Exporter Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_HEADERS=

# Resource Attributes
OTEL_RESOURCE_ATTRIBUTES=service.name=agentic-core,service.version=1.0.0,deployment.environment=development

# Sampling Configuration
OTEL_TRACES_SAMPLER=traceidratio
OTEL_TRACES_SAMPLER_ARG=1.0

# Service-specific Configuration
OTEL_SERVICE_NAME=aob-api
OTEL_SERVICE_VERSION=1.0.0
```

### Collector Configuration
Example OpenTelemetry Collector configuration (`otel-collector.yaml`):
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  resource:
    attributes:
      - key: environment
        value: development
        action: upsert

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [jaeger, logging]
```

## Span Attributes

### Common Attributes
All spans include these standard attributes:

```python
# Service Information
"service.name": "aob-api"
"service.version": "1.0.0"
"deployment.environment": "development"

# Request Information
"http.method": "POST"
"http.url": "http://localhost:8000/workflows/start"
"http.status_code": 200
"http.user_agent": "curl/7.68.0"

# Workflow Information
"workflow.id": "demo-workflow-123"
"workflow.name": "demo"
"workflow.version": "1.0.0"

# Tenant Information
"tenant.id": "acme-corp"
"user.id": "user-123"
```

### Node Execution Attributes
```python
# Node-specific attributes
"node.id": "n1"
"node.name": "uppercase"
"node.kind": "task"
"node.expression": "ctx.bag"

# Execution context
"execution.attempt": 1
"execution.max_attempts": 3
"execution.retry_count": 0
```

### Policy Evaluation Attributes
```python
# Policy-specific attributes
"policy.decision": "allow"
"policy.rules": ["require_human_for_risk_high"]
"policy.evaluation_time_ms": 15
"policy.opa_url": "http://localhost:8181"
```

### Tool/Model Call Attributes
```python
# Tool call attributes
"tool.name": "cmms.create_workorder"
"tool.endpoint": "https://tools.company/cmms"
"tool.method": "POST"
"tool.status_code": 200
"tool.duration_ms": 250

# Model call attributes
"model.name": "gpt-4"
"model.provider": "openai"
"model.tier": "premium"
"model.tokens_input": 150
"model.tokens_output": 75
"model.cost_usd": 0.003
```

### Database Operation Attributes
```python
# Database attributes
"db.system": "postgresql"
"db.name": "aob"
"db.operation": "INSERT"
"db.table": "events"
"db.rows_affected": 1
"db.duration_ms": 45
```

### Event Publishing Attributes
```python
# Event publishing attributes
"messaging.system": "kafka"
"messaging.destination": "aob.events"
"messaging.destination_kind": "topic"
"messaging.message_id": "msg-123"
"messaging.payload_size_bytes": 1024
```

## Implementation Details

### API Service Tracing
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracing
tracer = trace.get_tracer(__name__)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Custom span for workflow execution
with tracer.start_as_current_span("workflow.execution") as span:
    span.set_attribute("workflow.id", workflow_id)
    span.set_attribute("workflow.name", workflow.name)
    # ... workflow execution logic
```

### Engine Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def execute_node(self, node: Node, ctx: Context) -> Any:
    with tracer.start_as_current_span("node.execution") as span:
        span.set_attribute("node.id", node.id)
        span.set_attribute("node.name", node.name)
        span.set_attribute("node.kind", node.kind)
        
        # Policy evaluation
        with tracer.start_as_current_span("policy.evaluation") as policy_span:
            policy_span.set_attribute("policy.rules", edge.policies)
            decision = await self.policy_guard.check(ctx, edge)
            policy_span.set_attribute("policy.decision", decision)
        
        # Node execution
        result = await node.execute(ctx)
        span.set_attribute("execution.success", True)
        return result
```

### Policy Guard Tracing
```python
async def check(self, ctx: Context, edge: Edge) -> bool:
    with tracer.start_as_current_span("policy.check") as span:
        span.set_attribute("policy.rules", edge.policies)
        span.set_attribute("policy.edge", f"{edge.from_node}->{edge.to_node}")
        
        try:
            decision = await self.evaluator.evaluate(ctx, edge)
            span.set_attribute("policy.decision", decision)
            span.set_attribute("policy.evaluation_time_ms", evaluation_time)
            return decision
        except Exception as e:
            span.set_attribute("policy.error", str(e))
            span.set_attribute("policy.decision", False)
            raise
```

## Visualization Platforms

### Jaeger
```bash
# Start Jaeger all-in-one
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14250:14250 \
  jaegertracing/all-in-one:latest

# Access UI: http://localhost:16686
```

### Grafana Tempo
```yaml
# docker-compose.yml
version: '3.8'
services:
  tempo:
    image: grafana/tempo:latest
    ports:
      - "3200:3200"   # tempo
      - "4317:4317"   # otlp grpc
      - "4318:4318"   # otlp http
    command: [ "-config.file=/etc/tempo.yaml" ]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
```

### Datadog
```bash
# Set Datadog OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=https://trace.agent.datadoghq.com:4318
export OTEL_EXPORTER_OTLP_HEADERS=dd-api-key=YOUR_API_KEY
```

### New Relic
```bash
# Set New Relic OTLP endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net:4318
export OTEL_EXPORTER_OTLP_HEADERS=api-key=YOUR_LICENSE_KEY
```

## Querying and Analysis

### Jaeger Query Examples
```bash
# Find traces by service
curl "http://localhost:16686/api/traces?service=aob-api"

# Find traces by operation
curl "http://localhost:16686/api/traces?operation=workflow.execution"

# Find traces by tag
curl "http://localhost:16686/api/traces?tags=workflow.id:demo-workflow-123"
```

### Grafana Queries
```promql
# Trace duration histogram
histogram_quantile(0.95, 
  rate(traces_duration_bucket[5m])
)

# Error rate by service
rate(traces_total{status="error"}[5m]) / 
rate(traces_total[5m])
```

## Performance Considerations

### Sampling
Configure sampling to balance observability with performance:

```python
# Probabilistic sampling (10% of traces)
OTEL_TRACES_SAMPLER=traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1

# Head-based sampling
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
```

### Batch Processing
```python
# Batch processor configuration
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter=otlp_exporter,
    max_export_batch_size=512,
    export_timeout_millis=30000,
    schedule_delay_millis=5000
)
```

### Resource Limits
```python
# Limit span attributes
OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT=2048
OTEL_ATTRIBUTE_COUNT_LIMIT=128
OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT=128
```

## Monitoring and Alerting

### Key Metrics
- **Trace Duration**: P95, P99 latency by operation
- **Error Rate**: Percentage of failed traces
- **Throughput**: Traces per second by service
- **Sampling Rate**: Actual vs configured sampling

### Alerting Rules
```yaml
# Prometheus alerting rules
groups:
  - name: tracing
    rules:
      - alert: HighTraceLatency
        expr: histogram_quantile(0.95, rate(traces_duration_bucket[5m])) > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High trace latency detected"
          
      - alert: HighErrorRate
        expr: rate(traces_total{status="error"}[5m]) / rate(traces_total[5m]) > 0.05
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in traces"
```

## Troubleshooting

### Common Issues

1. **No traces appearing**
   - Check `OTEL_EXPORTER_OTLP_ENDPOINT` is set correctly
   - Verify collector is running and accessible
   - Check sampling configuration

2. **High memory usage**
   - Reduce batch size
   - Increase export frequency
   - Enable span limits

3. **Missing attributes**
   - Check attribute count limits
   - Verify span instrumentation
   - Check resource configuration

### Debug Commands
```bash
# Test OTLP endpoint
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'

# Check collector logs
docker logs otel-collector

# Verify span export
curl http://localhost:16686/api/services
```

## Best Practices

### Span Naming
- Use consistent naming conventions
- Include operation type: `workflow.start`, `node.execute`, `policy.check`
- Avoid high cardinality values in span names

### Attribute Management
- Use semantic conventions for standard attributes
- Limit custom attributes to essential information
- Avoid sensitive data in attributes

### Error Handling
- Always set error status on failed operations
- Include error details in span attributes
- Use proper error propagation

### Performance
- Use async instrumentation where possible
- Batch span exports efficiently
- Monitor instrumentation overhead

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Semantic Conventions](https://opentelemetry.io/docs/specs/otel/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Tempo](https://grafana.com/docs/tempo/)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/distributions/)
