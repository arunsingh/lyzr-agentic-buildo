#!/bin/bash

# AOB Platform - Comprehensive Monitoring Setup Script
# This script sets up Prometheus, Grafana, Jaeger, and OpenTelemetry Collector

set -e

echo "🚀 Setting up AOB Platform Monitoring Stack..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create monitoring directories
print_status "Creating monitoring directories..."
mkdir -p monitoring/prometheus/rules
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/alertmanager
mkdir -p monitoring/otel-collector

# Create Prometheus rules
print_status "Creating Prometheus alerting rules..."
cat > monitoring/prometheus/rules/aob-alerts.yml << 'EOF'
groups:
  - name: aob-platform
    rules:
      - alert: HighErrorRate
        expr: sum(rate(aob_errors_total[5m])) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighRequestLatency
        expr: histogram_quantile(0.95, rate(aob_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency"
          description: "95th percentile latency is {{ $value }} seconds"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "Service {{ $labels.job }} is down"

      - alert: HighMemoryUsage
        expr: aob_memory_usage_bytes / (1024^3) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }} GB"

      - alert: CircuitBreakerOpen
        expr: aob_circuit_breaker_state == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker is open"
          description: "Circuit breaker {{ $labels.name }} is open"
EOF

# Create Grafana datasource configuration
print_status "Creating Grafana datasource configuration..."
cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard provisioning
print_status "Creating Grafana dashboard provisioning..."
cat > monitoring/grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

# Create AlertManager configuration
print_status "Creating AlertManager configuration..."
cat > monitoring/alertmanager/alertmanager.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@aob-platform.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/'

  - name: 'email'
    email_configs:
      - to: 'admin@aob-platform.com'
        subject: 'AOB Platform Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
EOF

# Start monitoring stack
print_status "Starting monitoring stack..."
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service health
print_status "Checking service health..."

services=("prometheus:9090" "grafana:3000" "jaeger:16686" "alertmanager:9093" "otel-collector:8888")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s "http://localhost:$port" > /dev/null 2>&1; then
        print_success "$name is healthy"
    else
        print_warning "$name is not responding"
    fi
done

# Import Grafana dashboards
print_status "Importing Grafana dashboards..."
sleep 10

# Function to import dashboard
import_dashboard() {
    local dashboard_file=$1
    local dashboard_name=$2
    
    if [ -f "$dashboard_file" ]; then
        curl -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Basic YWRtaW46YWRtaW4=" \
            -d @"$dashboard_file" \
            "http://localhost:3000/api/dashboards/db" > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            print_success "Imported dashboard: $dashboard_name"
        else
            print_warning "Failed to import dashboard: $dashboard_name"
        fi
    else
        print_warning "Dashboard file not found: $dashboard_file"
    fi
}

# Import dashboards
import_dashboard "grafana/dashboards/aob-platform.json" "AOB Platform Monitoring"
import_dashboard "grafana/dashboards/aob-tracing.json" "AOB Distributed Tracing"

# Create monitoring startup script
print_status "Creating monitoring startup script..."
cat > start-monitoring.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting AOB Platform Monitoring Stack..."

# Start monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

echo "✅ Monitoring stack started!"
echo ""
echo "📊 Access URLs:"
echo "  Grafana:     http://localhost:3000 (admin/admin)"
echo "  Prometheus:  http://localhost:9090"
echo "  Jaeger:      http://localhost:16686"
echo "  AlertManager: http://localhost:9093"
echo ""
echo "🔧 To stop monitoring:"
echo "  docker-compose -f monitoring/docker-compose.monitoring.yml down"
EOF

chmod +x start-monitoring.sh

# Create monitoring stop script
print_status "Creating monitoring stop script..."
cat > stop-monitoring.sh << 'EOF'
#!/bin/bash

echo "🛑 Stopping AOB Platform Monitoring Stack..."

# Stop monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml down

echo "✅ Monitoring stack stopped!"
EOF

chmod +x stop-monitoring.sh

# Create monitoring status script
print_status "Creating monitoring status script..."
cat > status-monitoring.sh << 'EOF'
#!/bin/bash

echo "📊 AOB Platform Monitoring Status"
echo "================================="

services=("prometheus:9090" "grafana:3000" "jaeger:16686" "alertmanager:9093" "otel-collector:8888")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s "http://localhost:$port" > /dev/null 2>&1; then
        echo "✅ $name: http://localhost:$port"
    else
        echo "❌ $name: Not responding"
    fi
done

echo ""
echo "📈 Container Status:"
docker-compose -f monitoring/docker-compose.monitoring.yml ps
EOF

chmod +x status-monitoring.sh

# Create comprehensive monitoring guide
print_status "Creating monitoring guide..."
cat > MONITORING_GUIDE.md << 'EOF'
# AOB Platform Monitoring Guide

## Overview

The AOB Platform includes comprehensive monitoring with:
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing
- **OpenTelemetry Collector**: Telemetry data processing
- **AlertManager**: Alert routing and notification

## Quick Start

### Start Monitoring
```bash
./start-monitoring.sh
```

### Stop Monitoring
```bash
./stop-monitoring.sh
```

### Check Status
```bash
./status-monitoring.sh
```

## Access URLs

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **AlertManager**: http://localhost:9093

## Dashboards

### AOB Platform Monitoring
- Request rate and duration
- Error rates and types
- Workflow execution metrics
- Policy decision metrics
- Resource usage

### AOB Distributed Tracing
- Trace rate and duration
- Span distribution
- Error tracking
- Service dependencies

## Alerting Rules

The platform includes pre-configured alerts for:
- High error rates
- High request latency
- Service downtime
- High memory usage
- Circuit breaker activation

## Custom Metrics

### Application Metrics
- `aob_requests_total`: Total requests
- `aob_request_duration_seconds`: Request duration
- `aob_errors_total`: Error count
- `aob_workflows_total`: Workflow executions
- `aob_policy_decisions_total`: Policy decisions

### Infrastructure Metrics
- `aob_memory_usage_bytes`: Memory usage
- `aob_active_connections`: Active connections
- `aob_circuit_breaker_state`: Circuit breaker state

## Troubleshooting

### Service Not Responding
1. Check container status: `docker-compose -f monitoring/docker-compose.monitoring.yml ps`
2. Check logs: `docker-compose -f monitoring/docker-compose.monitoring.yml logs <service>`
3. Restart service: `docker-compose -f monitoring/docker-compose.monitoring.yml restart <service>`

### No Data in Grafana
1. Verify Prometheus is scraping metrics
2. Check data source configuration
3. Verify time range in dashboard

### Missing Traces in Jaeger
1. Check OpenTelemetry Collector logs
2. Verify OTLP endpoint configuration
3. Check application instrumentation

## Advanced Configuration

### Adding Custom Dashboards
1. Create dashboard JSON file in `monitoring/grafana/dashboards/`
2. Restart Grafana: `docker-compose -f monitoring/docker-compose.monitoring.yml restart grafana`

### Adding Custom Alerts
1. Edit `monitoring/prometheus/rules/aob-alerts.yml`
2. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`

### Custom Metrics
Add custom metrics in your application using the telemetry module:
```python
from agentic_core.telemetry import telemetry

# Record custom metric
telemetry.metrics["custom_metric"].add(1, {"label": "value"})
```

## Performance Tuning

### Prometheus
- Adjust scrape intervals in `prometheus.yml`
- Configure retention policies
- Set up remote storage for long-term retention

### Grafana
- Configure caching
- Set up data source proxies
- Optimize dashboard queries

### Jaeger
- Configure sampling rates
- Set up storage backends
- Tune collector settings
EOF

print_success "Monitoring setup completed!"
echo ""
echo "📊 Access URLs:"
echo "  Grafana:     http://localhost:3000 (admin/admin)"
echo "  Prometheus:  http://localhost:9090"
echo "  Jaeger:      http://localhost:16686"
echo "  AlertManager: http://localhost:9093"
echo ""
echo "📚 Documentation: MONITORING_GUIDE.md"
echo ""
echo "🚀 To start monitoring: ./start-monitoring.sh"
echo "🛑 To stop monitoring: ./stop-monitoring.sh"
echo "📈 To check status: ./status-monitoring.sh"
