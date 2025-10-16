# Netdata Monitoring Setup for AOB Platform

## 🎯 **Overview**

This document provides comprehensive instructions for setting up Netdata monitoring for the AOB Platform, covering all core infrastructure, applications, and components with real-time monitoring capabilities.

## 🚀 **What is Netdata?**

Netdata is an open-source, real-time performance and health monitoring solution that provides:

- **Real-time Monitoring**: Live metrics collection and visualization
- **Zero Configuration**: Automatic discovery and monitoring of system resources
- **Distributed Monitoring**: Multi-node monitoring with streaming capabilities
- **Comprehensive Coverage**: System, application, and container monitoring
- **Beautiful Dashboards**: Professional, responsive web interface
- **Alerting**: Built-in alerting and notification system
- **API Access**: RESTful API for integration and automation

## 📊 **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    Netdata Monitoring Stack                │
├─────────────────────────────────────────────────────────────┤
│  Main Netdata Instance (Parent Node) - Port 19999         │
│  • Central dashboard and API                               │
│  • Data aggregation and storage                            │
│  • Alerting and notifications                              │
│  • Streaming coordination                                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                Child Netdata Instances                     │
├─────────────────────────────────────────────────────────────┤
│  API Service (19998)    │  Worker Service (19997)         │
│  Audit Service (19996)  │  Model Gateway (19995)          │
│  Tool Gateway (19994)   │  Tenant Manager (19993)         │
│  Session Service (19992)│  Metering Service (19991)       │
│  Execution Service (19990)│ Agent Registry (19989)       │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                Monitored Components                        │
├─────────────────────────────────────────────────────────────┤
│  System Resources  │  Applications  │  Containers          │
│  • CPU, Memory     │  • AOB Services│  • Docker            │
│  • Disk, Network   │  • Databases   │  • Kubernetes        │
│  • Processes       │  • Message Q   │  • Microservices     │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ **Installation & Setup**

### **Prerequisites**

- Docker and Docker Compose installed
- At least 2GB RAM available
- Ports 19989-19999 available
- Network access to monitored services

### **Quick Setup**

1. **Run the setup script**:
   ```bash
   ./setup-netdata.sh
   ```

2. **Start Netdata services**:
   ```bash
   cd monitoring/netdata
   docker-compose -f docker-compose.netdata.yml up -d
   ```

3. **Access the dashboard**:
   - Main Dashboard: http://localhost:19999
   - Individual Services: http://localhost:19998-19989

### **Manual Setup**

1. **Create directories**:
   ```bash
   mkdir -p monitoring/netdata/{conf.d,health.d,stream.d,python.d,go.d,node.d,logs}
   ```

2. **Copy configuration files**:
   ```bash
   cp monitoring/netdata/netdata.conf monitoring/netdata/conf.d/
   cp monitoring/netdata/stream.conf monitoring/netdata/stream.d/
   cp monitoring/netdata/health.conf monitoring/netdata/health.d/
   ```

3. **Generate API keys**:
   ```bash
   # Generate API key
   API_KEY=$(openssl rand -hex 32)
   echo "NETDATA_API_KEY=${API_KEY}" > monitoring/netdata/.env
   
   # Generate claim token
   CLAIM_TOKEN=$(openssl rand -hex 32)
   echo "NETDATA_CLAIM_TOKEN=${CLAIM_TOKEN}" >> monitoring/netdata/.env
   ```

4. **Start services**:
   ```bash
   docker-compose -f monitoring/netdata/docker-compose.netdata.yml up -d
   ```

## 📈 **Monitoring Capabilities**

### **System Monitoring**

- **CPU Usage**: Per-core utilization, load average, context switches
- **Memory Usage**: RAM, swap, buffers, cache usage
- **Disk I/O**: Read/write operations, disk space, I/O wait
- **Network Traffic**: Interface statistics, packet rates, bandwidth
- **Process Monitoring**: Running processes, resource usage per process
- **System Load**: Load average, uptime, system calls

### **Application Monitoring**

- **AOB API Service**: Request rates, response times, error rates
- **Worker Service**: Queue length, processing time, throughput
- **Audit Service**: Decision records, export operations, storage usage
- **Model Gateway**: LLM requests, model performance, routing decisions
- **Tool Gateway**: MCP calls, policy evaluations, tool performance
- **Database Services**: Connection pools, query performance, locks
- **Message Queues**: Kafka topics, consumer lag, message rates

### **Container Monitoring**

- **Docker Containers**: Resource usage, health status, restart counts
- **Kubernetes Pods**: Pod status, resource limits, scaling events
- **Container Networks**: Network policies, service discovery
- **Storage Volumes**: Volume usage, mount points, I/O patterns

### **Custom Metrics**

- **Workflow Metrics**: Execution time, success rate, policy decisions
- **Business Metrics**: User activity, feature usage, performance KPIs
- **Security Metrics**: Authentication events, policy violations, access patterns
- **Cost Metrics**: Resource consumption, billing data, optimization opportunities

## 🎛️ **Dashboard Features**

### **Main Dashboard (Port 19999)**

- **System Overview**: Real-time system health and performance
- **Service Status**: All AOB services status and metrics
- **Alert Summary**: Active alerts and notifications
- **Resource Usage**: CPU, memory, disk, network utilization
- **Process List**: Running processes and resource consumption
- **Network Map**: Service dependencies and communication patterns

### **Service-Specific Dashboards**

Each service has its own dedicated dashboard with:

- **Service Health**: Status, uptime, error rates
- **Performance Metrics**: Response times, throughput, latency
- **Resource Usage**: CPU, memory, disk, network per service
- **Custom Metrics**: Service-specific KPIs and business metrics
- **Alert History**: Service-specific alerts and notifications

### **Real-time Features**

- **Live Updates**: Metrics update every second
- **Interactive Charts**: Zoom, pan, and filter capabilities
- **Drill-down**: Click to explore detailed metrics
- **Export Options**: PNG, SVG, CSV export capabilities
- **Mobile Responsive**: Optimized for mobile devices

## 🔔 **Alerting & Notifications**

### **Built-in Alerts**

- **System Alerts**: High CPU, memory, disk usage
- **Service Alerts**: Service down, high error rates, slow response
- **Application Alerts**: Workflow failures, policy violations, quota exceeded
- **Infrastructure Alerts**: Container failures, network issues, storage problems

### **Alert Configuration**

```bash
# Example alert configuration
[system.cpu]
    enabled = yes
    warn threshold = 80
    crit threshold = 95
    
[aob-api.response_time]
    enabled = yes
    warn threshold = 1000
    crit threshold = 5000
```

### **Notification Channels**

- **Email**: SMTP-based email notifications
- **Slack**: Slack webhook integration
- **Discord**: Discord webhook integration
- **Webhook**: Custom HTTP endpoint notifications
- **PagerDuty**: PagerDuty integration
- **Custom**: Custom notification scripts

## 🔌 **API Integration**

### **REST API**

Netdata provides a comprehensive REST API for:

- **Metrics Access**: Retrieve current and historical metrics
- **Health Checks**: Service health and status information
- **Alert Management**: Alert configuration and status
- **Streaming Control**: Manage data streaming between nodes

### **API Examples**

```bash
# Get system info
curl http://localhost:19999/api/v1/info

# Get CPU metrics
curl http://localhost:19999/api/v1/data?chart=system.cpu

# Get health status
curl http://localhost:19999/api/v1/health

# Get alerts
curl http://localhost:19999/api/v1/alarms
```

### **Integration with AOB Platform**

The Netdata integration component in the AOB UI provides:

- **Service Status**: Real-time service health monitoring
- **Quick Access**: Direct links to service dashboards
- **Metrics Overview**: Key metrics and performance indicators
- **Alert Management**: View and manage active alerts

## 📊 **Performance & Scalability**

### **Resource Requirements**

- **CPU**: Minimal impact (< 1% per node)
- **Memory**: ~50MB per node
- **Disk**: ~100MB for configuration and logs
- **Network**: Minimal bandwidth usage

### **Scalability Features**

- **Horizontal Scaling**: Add more nodes as needed
- **Data Streaming**: Efficient data aggregation
- **Compression**: LZ4 compression for streaming
- **Caching**: Intelligent caching for performance
- **Load Balancing**: Distribute monitoring load

### **Performance Optimization**

- **Efficient Collection**: Optimized data collection algorithms
- **Smart Sampling**: Adaptive sampling based on system load
- **Memory Management**: Efficient memory usage patterns
- **Network Optimization**: Minimized network overhead

## 🔧 **Configuration Management**

### **Configuration Files**

- **netdata.conf**: Main configuration file
- **stream.conf**: Streaming configuration
- **health.conf**: Health checks and alerts
- **python.d/**: Python plugin configurations
- **go.d/**: Go plugin configurations
- **node.d/**: Node.js plugin configurations

### **Environment Variables**

```bash
# Core settings
NETDATA_API_KEY=your-api-key
NETDATA_CLAIM_TOKEN=your-claim-token
NETDATA_CLAIM_URL=https://app.netdata.cloud

# Performance tuning
NETDATA_MEMORY_MODE=ram
NETDATA_HISTORY=3600
NETDATA_UPDATE_EVERY=1

# Security settings
NETDATA_ALLOW_CONNECTIONS_FROM=*
NETDATA_ALLOW_STREAMING_FROM=*
NETDATA_ALLOW_COMMANDS_FROM=*
```

### **Plugin Configuration**

```bash
# Enable specific plugins
[plugins]
    python.d = yes
    go.d = yes
    node.d = yes
    apps = yes
    cgroup = yes
    perf = yes
    diskspace = yes
    tc = yes
    idlejitter = yes
    check = yes
    proc = yes
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Service Not Starting**
```bash
# Check Docker logs
docker-compose -f monitoring/netdata/docker-compose.netdata.yml logs netdata-parent

# Check service status
docker-compose -f monitoring/netdata/docker-compose.netdata.yml ps
```

#### **No Metrics Appearing**
```bash
# Check plugin status
curl http://localhost:19999/api/v1/charts

# Check plugin configuration
curl http://localhost:19999/api/v1/plugins
```

#### **High Resource Usage**
```bash
# Check Netdata resource usage
docker stats netdata-parent

# Adjust memory mode
echo "memory mode = ram" >> monitoring/netdata/conf.d/netdata.conf
```

#### **Streaming Issues**
```bash
# Check streaming status
curl http://localhost:19999/api/v1/streaming

# Verify API keys
grep NETDATA_API_KEY monitoring/netdata/.env
```

### **Debug Commands**

```bash
# Check Netdata status
curl http://localhost:19999/api/v1/info

# Check health status
curl http://localhost:19999/api/v1/health

# Check charts
curl http://localhost:19999/api/v1/charts

# Check alarms
curl http://localhost:19999/api/v1/alarms

# Check plugins
curl http://localhost:19999/api/v1/plugins
```

### **Log Analysis**

```bash
# View Netdata logs
docker-compose -f monitoring/netdata/docker-compose.netdata.yml logs -f netdata-parent

# Check specific service logs
docker-compose -f monitoring/netdata/docker-compose.netdata.yml logs netdata-api

# View health check logs
tail -f monitoring/netdata/logs/health.log
```

## 📚 **Best Practices**

### **Monitoring Strategy**

1. **Start Simple**: Begin with basic system monitoring
2. **Add Gradually**: Add application monitoring incrementally
3. **Focus on KPIs**: Monitor key performance indicators
4. **Set Alerts**: Configure meaningful alerts and thresholds
5. **Regular Review**: Review and adjust monitoring regularly

### **Alert Management**

1. **Meaningful Thresholds**: Set realistic alert thresholds
2. **Avoid Alert Fatigue**: Don't over-alert on minor issues
3. **Escalation Policies**: Implement proper escalation procedures
4. **Regular Testing**: Test alerting mechanisms regularly
5. **Documentation**: Document alert procedures and responses

### **Performance Optimization**

1. **Resource Monitoring**: Monitor Netdata resource usage
2. **Data Retention**: Configure appropriate data retention
3. **Compression**: Enable compression for streaming
4. **Caching**: Use appropriate caching strategies
5. **Load Balancing**: Distribute monitoring load effectively

## 🔗 **Integration with AOB Platform**

### **UI Integration**

The Netdata integration is accessible through:

1. **Main Dashboard**: Navigate to "Monitoring" → "Netdata Monitoring"
2. **Service Overview**: View all service status and metrics
3. **Quick Access**: Direct links to individual service dashboards
4. **Real-time Updates**: Automatic status updates every 30 seconds

### **API Integration**

```typescript
// Example API integration
const checkServiceStatus = async (port: number) => {
  try {
    const response = await fetch(`http://localhost:${port}/api/v1/info`);
    return response.ok;
  } catch (error) {
    return false;
  }
};
```

### **Custom Dashboards**

Create custom dashboards for:

- **Business Metrics**: Workflow performance, user activity
- **Security Monitoring**: Authentication, policy violations
- **Cost Tracking**: Resource usage, billing metrics
- **Operational Metrics**: Service health, system performance

## 📈 **Future Enhancements**

### **Planned Features**

1. **Advanced Analytics**: Machine learning-based anomaly detection
2. **Custom Plugins**: AOB-specific monitoring plugins
3. **Integration APIs**: Enhanced API for platform integration
4. **Mobile App**: Dedicated mobile monitoring application
5. **Cloud Integration**: Cloud provider monitoring integration

### **Community Contributions**

- **Plugin Development**: Contribute custom monitoring plugins
- **Dashboard Templates**: Share dashboard configurations
- **Alert Rules**: Contribute alert rule templates
- **Documentation**: Improve documentation and guides

## 📞 **Support & Resources**

### **Documentation**

- **Official Docs**: https://docs.netdata.cloud/
- **API Reference**: https://docs.netdata.cloud/api/
- **Plugin Guide**: https://docs.netdata.cloud/collectors/
- **Alerting Guide**: https://docs.netdata.cloud/health/

### **Community**

- **GitHub**: https://github.com/netdata/netdata
- **Discord**: https://discord.gg/5ygS846fR6
- **Forum**: https://community.netdata.cloud/
- **Stack Overflow**: Tag: netdata

### **Professional Support**

- **Netdata Cloud**: https://app.netdata.cloud/
- **Enterprise Support**: https://www.netdata.cloud/enterprise/
- **Training**: https://www.netdata.cloud/training/
- **Consulting**: https://www.netdata.cloud/consulting/

---

**AOB Platform** - Comprehensive Netdata Monitoring
*Real-time monitoring for enterprise-grade agentic orchestration.*
