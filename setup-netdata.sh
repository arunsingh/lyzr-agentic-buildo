#!/bin/bash

# Netdata Setup Script for AOB Platform
# This script sets up Netdata monitoring for all core infrastructure and applications

set -e

echo "🚀 Setting up Netdata monitoring for AOB Platform..."

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
check_docker() {
    print_status "Checking Docker status..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose availability..."
    if ! docker compose version > /dev/null 2>&1; then
        print_error "Docker Compose is not available. Please ensure Docker Compose is installed and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Create Netdata directories
create_directories() {
    print_status "Creating Netdata directories..."
    
    # Create configuration directories
    mkdir -p monitoring/netdata/conf.d
    mkdir -p monitoring/netdata/health.d
    mkdir -p monitoring/netdata/stream.d
    mkdir -p monitoring/netdata/python.d
    mkdir -p monitoring/netdata/go.d
    mkdir -p monitoring/netdata/node.d
    
    # Create log directories
    mkdir -p monitoring/netdata/logs
    
    print_success "Netdata directories created"
}

# Copy configuration files
copy_configurations() {
    print_status "Copying Netdata configuration files..."
    
    # Copy main configuration
    if [ -f "monitoring/netdata/netdata.conf" ]; then
        cp monitoring/netdata/netdata.conf monitoring/netdata/conf.d/
        print_success "Main configuration copied"
    else
        print_warning "Main configuration file not found"
    fi
    
    # Copy streaming configuration
    if [ -f "monitoring/netdata/stream.conf" ]; then
        cp monitoring/netdata/stream.conf monitoring/netdata/stream.d/
        print_success "Streaming configuration copied"
    else
        print_warning "Streaming configuration file not found"
    fi
    
    # Copy health configuration
    if [ -f "monitoring/netdata/health.conf" ]; then
        cp monitoring/netdata/health.conf monitoring/netdata/health.d/
        print_success "Health configuration copied"
    else
        print_warning "Health configuration file not found"
    fi
}

# Create Netdata API key
create_api_key() {
    print_status "Creating Netdata API key..."
    
    # Generate a random API key
    API_KEY=$(openssl rand -hex 32)
    
    # Create API key file
    cat > monitoring/netdata/api_key.txt << EOF
# Netdata API Key for AOB Platform
# Generated on: $(date)
# Use this key for authentication between Netdata nodes

NETDATA_API_KEY=${API_KEY}
EOF
    
    print_success "API key created: ${API_KEY}"
    print_warning "Please save this API key securely: ${API_KEY}"
}

# Create Netdata claim token
create_claim_token() {
    print_status "Creating Netdata claim token..."
    
    # Generate a random claim token
    CLAIM_TOKEN=$(openssl rand -hex 32)
    
    # Create claim token file
    cat > monitoring/netdata/claim_token.txt << EOF
# Netdata Claim Token for AOB Platform
# Generated on: $(date)
# Use this token to claim your Netdata nodes

NETDATA_CLAIM_TOKEN=${CLAIM_TOKEN}
EOF
    
    print_success "Claim token created: ${CLAIM_TOKEN}"
    print_warning "Please save this claim token securely: ${CLAIM_TOKEN}"
}

# Create environment file
create_env_file() {
    print_status "Creating environment file..."
    
    # Read API key and claim token
    API_KEY=$(grep "NETDATA_API_KEY=" monitoring/netdata/api_key.txt | cut -d'=' -f2)
    CLAIM_TOKEN=$(grep "NETDATA_CLAIM_TOKEN=" monitoring/netdata/claim_token.txt | cut -d'=' -f2)
    
    # Create environment file
    cat > monitoring/netdata/.env << EOF
# Netdata Environment Variables for AOB Platform
# Generated on: $(date)

# API Key for authentication
NETDATA_API_KEY=${API_KEY}

# Claim Token for claiming nodes
NETDATA_CLAIM_TOKEN=${CLAIM_TOKEN}

# Claim URL (optional)
NETDATA_CLAIM_URL=https://app.netdata.cloud

# Claim Rooms (optional)
NETDATA_CLAIM_ROOMS=netdata-rooms

# Claim Proxy (optional)
NETDATA_CLAIM_PROXY=

# Claim Extra (optional)
NETDATA_CLAIM_EXTRA=
EOF
    
    print_success "Environment file created"
}

# Update Docker Compose file with environment variables
update_docker_compose() {
    print_status "Updating Docker Compose file with environment variables..."
    
    # Read environment variables
    source monitoring/netdata/.env
    
    # Update Docker Compose file
    sed -i.bak "s/netdata-api-key/${NETDATA_API_KEY}/g" monitoring/netdata/docker-compose.netdata.yml
    sed -i.bak "s/netdata-claim-token/${NETDATA_CLAIM_TOKEN}/g" monitoring/netdata/docker-compose.netdata.yml
    
    print_success "Docker Compose file updated"
}

# Start Netdata services
start_netdata() {
    print_status "Starting Netdata services..."
    
    # Change to monitoring directory
    cd monitoring/netdata
    
    # Start services
    docker compose -f docker-compose.netdata.yml up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check service status
    print_status "Checking service status..."
    docker compose -f docker-compose.netdata.yml ps
    
    print_success "Netdata services started"
}

# Verify Netdata installation
verify_installation() {
    print_status "Verifying Netdata installation..."
    
    # Check if main Netdata instance is running
    if curl -f http://localhost:19999/api/v1/info > /dev/null 2>&1; then
        print_success "Main Netdata instance is running on http://localhost:19999"
    else
        print_error "Main Netdata instance is not responding"
        return 1
    fi
    
    # Check if child instances are running
    for port in 19998 19997 19996 19995 19994 19993 19992 19991 19990 19989; do
        if curl -f http://localhost:${port}/api/v1/info > /dev/null 2>&1; then
            print_success "Netdata child instance is running on http://localhost:${port}"
        else
            print_warning "Netdata child instance on port ${port} is not responding"
        fi
    done
    
    print_success "Netdata installation verified"
}

# Create access URLs file
create_access_urls() {
    print_status "Creating access URLs file..."
    
    cat > monitoring/netdata/access_urls.txt << EOF
# Netdata Access URLs for AOB Platform
# Generated on: $(date)

# Main Netdata Instance (Parent Node)
Main Dashboard: http://localhost:19999
API: http://localhost:19999/api/v1/info
Health: http://localhost:19999/api/v1/health

# Child Netdata Instances
API Service: http://localhost:19998
Worker Service: http://localhost:19997
Audit Service: http://localhost:19996
Model Gateway: http://localhost:19995
Tool Gateway: http://localhost:19994
Tenant Manager: http://localhost:19993
Session Service: http://localhost:19992
Metering Service: http://localhost:19991
Execution Service: http://localhost:19990
Agent Registry: http://localhost:19989

# Streaming Status
Streaming Status: http://localhost:19999/api/v1/streaming
Streaming Info: http://localhost:19999/api/v1/streaming/info

# Health Checks
Health Status: http://localhost:19999/api/v1/health
Health Log: http://localhost:19999/api/v1/health/log

# Metrics
All Metrics: http://localhost:19999/api/v1/metrics
System Metrics: http://localhost:19999/api/v1/metrics/system
Application Metrics: http://localhost:19999/api/v1/metrics/applications
EOF
    
    print_success "Access URLs file created"
}

# Create monitoring dashboard
create_monitoring_dashboard() {
    print_status "Creating monitoring dashboard..."
    
    cat > monitoring/netdata/monitoring_dashboard.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AOB Platform - Netdata Monitoring Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h3 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .card a {
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 5px;
            transition: background 0.3s ease;
        }
        .card a:hover {
            background: #764ba2;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        .status.running {
            background: #d4edda;
            color: #155724;
        }
        .status.stopped {
            background: #f8d7da;
            color: #721c24;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: #333;
            color: white;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AOB Platform - Netdata Monitoring Dashboard</h1>
            <p>Comprehensive monitoring for all core infrastructure and applications</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>Main Dashboard</h3>
                <p>Central monitoring dashboard for the entire AOB platform</p>
                <a href="http://localhost:19999" target="_blank">Open Main Dashboard</a>
                <a href="http://localhost:19999/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>API Service</h3>
                <p>Monitor the main API service performance and health</p>
                <a href="http://localhost:19998" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19998/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Worker Service</h3>
                <p>Monitor background worker performance and queue status</p>
                <a href="http://localhost:19997" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19997/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Audit Service</h3>
                <p>Monitor audit service performance and decision records</p>
                <a href="http://localhost:19996" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19996/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Model Gateway</h3>
                <p>Monitor model gateway performance and LLM interactions</p>
                <a href="http://localhost:19995" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19995/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Tool Gateway</h3>
                <p>Monitor tool gateway performance and MCP interactions</p>
                <a href="http://localhost:19994" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19994/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Tenant Manager</h3>
                <p>Monitor tenant manager performance and multi-tenancy</p>
                <a href="http://localhost:19993" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19993/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Session Service</h3>
                <p>Monitor session service performance and HITL interactions</p>
                <a href="http://localhost:19992" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19992/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Metering Service</h3>
                <p>Monitor metering service performance and usage tracking</p>
                <a href="http://localhost:19991" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19991/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Execution Service</h3>
                <p>Monitor execution service performance and workflow execution</p>
                <a href="http://localhost:19990" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19990/api/v1/info" target="_blank">API Info</a>
            </div>
            
            <div class="card">
                <h3>Agent Registry</h3>
                <p>Monitor agent registry performance and agent management</p>
                <a href="http://localhost:19989" target="_blank">Open Dashboard</a>
                <a href="http://localhost:19989/api/v1/info" target="_blank">API Info</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated on: <span id="timestamp"></span></p>
            <p>AOB Platform - Comprehensive Monitoring with Netdata</p>
        </div>
    </div>
    
    <script>
        // Update timestamp
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // Check service status
        async function checkServiceStatus(port) {
            try {
                const response = await fetch(`http://localhost:${port}/api/v1/info`);
                return response.ok;
            } catch (error) {
                return false;
            }
        }
        
        // Update status indicators
        async function updateStatus() {
            const ports = [19999, 19998, 19997, 19996, 19995, 19994, 19993, 19992, 19991, 19990, 19989];
            for (const port of ports) {
                const isRunning = await checkServiceStatus(port);
                const statusElement = document.querySelector(`[data-port="${port}"]`);
                if (statusElement) {
                    statusElement.className = `status ${isRunning ? 'running' : 'stopped'}`;
                    statusElement.textContent = isRunning ? 'Running' : 'Stopped';
                }
            }
        }
        
        // Update status every 30 seconds
        setInterval(updateStatus, 30000);
        updateStatus();
    </script>
</body>
</html>
EOF
    
    print_success "Monitoring dashboard created"
}

# Main execution
main() {
    print_status "Starting Netdata setup for AOB Platform..."
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Setup Netdata
    create_directories
    copy_configurations
    create_api_key
    create_claim_token
    create_env_file
    update_docker_compose
    
    # Start services
    start_netdata
    
    # Verify installation
    verify_installation
    
    # Create access information
    create_access_urls
    create_monitoring_dashboard
    
    print_success "Netdata setup completed successfully!"
    print_status "Access URLs saved to: monitoring/netdata/access_urls.txt"
    print_status "Monitoring dashboard saved to: monitoring/netdata/monitoring_dashboard.html"
    print_status "Main Netdata dashboard: http://localhost:19999"
    
    echo ""
    print_status "Next steps:"
    echo "1. Open the monitoring dashboard: monitoring/netdata/monitoring_dashboard.html"
    echo "2. Access the main Netdata dashboard: http://localhost:19999"
    echo "3. Configure alerts and notifications as needed"
    echo "4. Integrate with your existing monitoring stack"
}

# Run main function
main "$@"
