# 🎯 **Netdata Dashboard Access Guide**

## 🚀 **Quick Access**

### **Main Dashboard**
- **URL**: http://localhost:19999
- **Status**: ✅ **RUNNING** (Healthy)
- **Version**: v1.44.3
- **Alarms**: 61 Normal, 0 Warning, 0 Critical

## 📊 **Dashboard Features**

### **Real-time Monitoring**
- **System Overview**: CPU, Memory, Disk, Network usage
- **Process Monitoring**: Running processes and resource consumption
- **Container Monitoring**: Docker containers and their metrics
- **Network Monitoring**: Interface statistics and traffic
- **File System**: Disk usage and I/O operations

### **Interactive Charts**
- **Live Updates**: Metrics update every second
- **Zoom & Pan**: Interactive chart navigation
- **Export Options**: PNG, SVG, CSV export
- **Mobile Responsive**: Optimized for mobile devices

### **Alerting System**
- **Built-in Alerts**: System health monitoring
- **Custom Thresholds**: Configurable warning/critical levels
- **Notification Channels**: Email, Slack, Discord, Webhook
- **Alert History**: Comprehensive alert tracking

## 🔗 **Access URLs**

### **Main Dashboard**
```
http://localhost:19999
```

### **API Endpoints**
```
System Info:     http://localhost:19999/api/v1/info
Health Status:   http://localhost:19999/api/v1/health
Charts Data:     http://localhost:19999/api/v1/charts
Alarms:          http://localhost:19999/api/v1/alarms
Metrics:         http://localhost:19999/api/v1/metrics
```

### **Service Management**
```bash
# Check status
docker compose -f monitoring/netdata/docker-compose.simple.yml ps

# View logs
docker compose -f monitoring/netdata/docker-compose.simple.yml logs -f

# Stop service
docker compose -f monitoring/netdata/docker-compose.simple.yml down

# Restart service
docker compose -f monitoring/netdata/docker-compose.simple.yml restart
```

## 🎛️ **Dashboard Navigation**

### **Main Sections**
1. **Overview**: System health summary
2. **System**: CPU, Memory, Disk, Network
3. **Applications**: Running applications and processes
4. **Containers**: Docker container monitoring
5. **Networking**: Network interfaces and traffic
6. **Storage**: File systems and disk usage

### **Key Metrics**
- **CPU Usage**: Per-core utilization and load average
- **Memory Usage**: RAM, swap, buffers, cache
- **Disk I/O**: Read/write operations and I/O wait
- **Network Traffic**: Interface statistics and bandwidth
- **Process List**: Running processes and resource usage

## 🔧 **Configuration**

### **Current Configuration**
- **Memory Mode**: RAM (fastest)
- **Update Frequency**: Every 1 second
- **History**: 3600 seconds (1 hour)
- **Plugins**: All enabled (Python, Go, Node.js, Apps, etc.)

### **Customization Options**
- **Dashboard Themes**: Light/Dark mode
- **Chart Types**: Line, area, bar charts
- **Time Ranges**: 1m, 5m, 15m, 1h, 4h, 1d, 1w
- **Export Formats**: PNG, SVG, CSV, JSON

## 📱 **Mobile Access**

The Netdata dashboard is fully responsive and optimized for mobile devices:
- **Touch Navigation**: Swipe and pinch gestures
- **Mobile Layout**: Optimized for small screens
- **Real-time Updates**: Live metrics on mobile
- **Offline Capability**: Cached data when offline

## 🚨 **Alerting**

### **Built-in Alerts**
- **High CPU Usage**: > 80% warning, > 95% critical
- **High Memory Usage**: > 80% warning, > 95% critical
- **Disk Space**: > 80% warning, > 95% critical
- **Network Issues**: Interface down or high errors
- **Process Issues**: High resource usage or crashes

### **Alert Configuration**
```bash
# View current alerts
curl http://localhost:19999/api/v1/alarms

# View alert history
curl http://localhost:19999/api/v1/alarms?all=1
```

## 🔌 **API Integration**

### **REST API Examples**
```bash
# Get system information
curl http://localhost:19999/api/v1/info

# Get specific chart data
curl http://localhost:19999/api/v1/data?chart=system.cpu

# Get health status
curl http://localhost:19999/api/v1/health

# Get all charts
curl http://localhost:19999/api/v1/charts
```

### **Integration with AOB Platform**
The Netdata integration component in the AOB UI provides:
- **Service Status**: Real-time service health monitoring
- **Quick Access**: Direct links to service dashboards
- **Metrics Overview**: Key metrics and performance indicators
- **Alert Management**: View and manage active alerts

## 🎯 **Next Steps**

### **Immediate Actions**
1. **Open Dashboard**: http://localhost:19999
2. **Explore Metrics**: Click on different charts and sections
3. **Configure Alerts**: Set up custom alert thresholds
4. **Export Data**: Use export options for reports

### **Advanced Features**
1. **Custom Dashboards**: Create personalized views
2. **API Integration**: Integrate with AOB Platform
3. **Alert Notifications**: Configure email/Slack notifications
4. **Data Export**: Set up automated data exports

## 🏆 **Success Metrics**

✅ **Netdata Instance**: Running and healthy
✅ **Dashboard Access**: Available at http://localhost:19999
✅ **API Endpoints**: All endpoints responding
✅ **Real-time Monitoring**: Live metrics updating
✅ **Mobile Support**: Responsive design working
✅ **Alert System**: 61 normal alerts, 0 warnings/critical

---

**AOB Platform** - Netdata Monitoring Dashboard
*Real-time monitoring for enterprise-grade agentic orchestration.*
