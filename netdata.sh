#!/bin/bash

# Netdata Quick Start Script for AOB Platform
# This script provides quick access to Netdata monitoring functions

set -e

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

# Function to show usage
show_usage() {
    echo "Netdata Quick Start Script for AOB Platform"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup       - Set up Netdata monitoring"
    echo "  start       - Start Netdata services"
    echo "  stop        - Stop Netdata services"
    echo "  restart     - Restart Netdata services"
    echo "  status      - Check service status"
    echo "  logs        - View service logs"
    echo "  dashboard   - Open main dashboard"
    echo "  services    - List all service dashboards"
    echo "  health      - Check health status"
    echo "  api         - Test API endpoints"
    echo "  cleanup     - Clean up Netdata data"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 dashboard"
}

# Function to setup Netdata
setup_netdata() {
    print_status "Setting up Netdata monitoring..."
    
    if [ -f "setup-netdata.sh" ]; then
        ./setup-netdata.sh
    else
        print_error "Setup script not found. Please run from the project root directory."
        exit 1
    fi
}

# Function to start Netdata services
start_netdata() {
    print_status "Starting Netdata services..."
    
    if [ -f "monitoring/netdata/docker-compose.netdata.yml" ]; then
        cd monitoring/netdata
        docker compose -f docker-compose.netdata.yml up -d
        cd ../..
        print_success "Netdata services started"
    else
        print_error "Docker Compose file not found. Please run setup first."
        exit 1
    fi
}

# Function to stop Netdata services
stop_netdata() {
    print_status "Stopping Netdata services..."
    
    if [ -f "monitoring/netdata/docker-compose.netdata.yml" ]; then
        cd monitoring/netdata
        docker compose -f docker-compose.netdata.yml down
        cd ../..
        print_success "Netdata services stopped"
    else
        print_error "Docker Compose file not found."
        exit 1
    fi
}

# Function to restart Netdata services
restart_netdata() {
    print_status "Restarting Netdata services..."
    stop_netdata
    sleep 5
    start_netdata
}

# Function to check service status
check_status() {
    print_status "Checking Netdata service status..."
    
    if [ -f "monitoring/netdata/docker-compose.netdata.yml" ]; then
        cd monitoring/netdata
        docker compose -f docker-compose.netdata.yml ps
        cd ../..
    else
        print_error "Docker Compose file not found."
        exit 1
    fi
}

# Function to view logs
view_logs() {
    print_status "Viewing Netdata service logs..."
    
    if [ -f "monitoring/netdata/docker-compose.netdata.yml" ]; then
        cd monitoring/netdata
        docker compose -f docker-compose.netdata.yml logs -f
        cd ../..
    else
        print_error "Docker Compose file not found."
        exit 1
    fi
}

# Function to open dashboard
open_dashboard() {
    print_status "Opening Netdata main dashboard..."
    
    if command -v open > /dev/null 2>&1; then
        open http://localhost:19999
    elif command -v xdg-open > /dev/null 2>&1; then
        xdg-open http://localhost:19999
    elif command -v start > /dev/null 2>&1; then
        start http://localhost:19999
    else
        print_warning "Cannot open browser automatically. Please open http://localhost:19999 manually."
    fi
}

# Function to list service dashboards
list_services() {
    print_status "Netdata Service Dashboards:"
    echo ""
    echo "Main Dashboard:     http://localhost:19999"
    echo "API Service:       http://localhost:19998"
    echo "Worker Service:    http://localhost:19997"
    echo "Audit Service:     http://localhost:19996"
    echo "Model Gateway:     http://localhost:19995"
    echo "Tool Gateway:      http://localhost:19994"
    echo "Tenant Manager:    http://localhost:19993"
    echo "Session Service:   http://localhost:19992"
    echo "Metering Service:  http://localhost:19991"
    echo "Execution Service: http://localhost:19990"
    echo "Agent Registry:    http://localhost:19989"
    echo ""
}

# Function to check health
check_health() {
    print_status "Checking Netdata health status..."
    
    # Check main instance
    if curl -f http://localhost:19999/api/v1/info > /dev/null 2>&1; then
        print_success "Main Netdata instance is healthy"
    else
        print_error "Main Netdata instance is not responding"
    fi
    
    # Check child instances
    for port in 19998 19997 19996 19995 19994 19993 19992 19991 19990 19989; do
        if curl -f http://localhost:${port}/api/v1/info > /dev/null 2>&1; then
            print_success "Netdata instance on port ${port} is healthy"
        else
            print_warning "Netdata instance on port ${port} is not responding"
        fi
    done
}

# Function to test API
test_api() {
    print_status "Testing Netdata API endpoints..."
    
    # Test main API
    echo "Testing main API..."
    curl -s http://localhost:19999/api/v1/info | jq '.' 2>/dev/null || echo "Main API test failed"
    
    # Test health API
    echo "Testing health API..."
    curl -s http://localhost:19999/api/v1/health | jq '.' 2>/dev/null || echo "Health API test failed"
    
    # Test charts API
    echo "Testing charts API..."
    curl -s http://localhost:19999/api/v1/charts | jq '.charts | keys' 2>/dev/null || echo "Charts API test failed"
}

# Function to cleanup
cleanup_netdata() {
    print_warning "This will remove all Netdata data and configurations."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up Netdata..."
        
        # Stop services
        stop_netdata
        
        # Remove volumes
        if [ -f "monitoring/netdata/docker-compose.netdata.yml" ]; then
            cd monitoring/netdata
            docker compose -f docker-compose.netdata.yml down -v
            cd ../..
        fi
        
        # Remove configuration files
        rm -rf monitoring/netdata/conf.d
        rm -rf monitoring/netdata/health.d
        rm -rf monitoring/netdata/stream.d
        rm -rf monitoring/netdata/python.d
        rm -rf monitoring/netdata/go.d
        rm -rf monitoring/netdata/node.d
        rm -rf monitoring/netdata/logs
        rm -f monitoring/netdata/.env
        rm -f monitoring/netdata/api_key.txt
        rm -f monitoring/netdata/claim_token.txt
        rm -f monitoring/netdata/access_urls.txt
        rm -f monitoring/netdata/monitoring_dashboard.html
        
        print_success "Netdata cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Main execution
main() {
    case "${1:-help}" in
        setup)
            setup_netdata
            ;;
        start)
            start_netdata
            ;;
        stop)
            stop_netdata
            ;;
        restart)
            restart_netdata
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        dashboard)
            open_dashboard
            ;;
        services)
            list_services
            ;;
        health)
            check_health
            ;;
        api)
            test_api
            ;;
        cleanup)
            cleanup_netdata
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
