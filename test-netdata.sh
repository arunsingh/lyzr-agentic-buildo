#!/bin/bash

# Netdata Dashboard Test Script
# This script tests all the key features of the Netdata dashboard

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

# Test Netdata API endpoints
test_api_endpoints() {
    print_status "Testing Netdata API endpoints..."
    
    # Test main info endpoint
    if curl -f -s http://localhost:19999/api/v1/info > /dev/null 2>&1; then
        print_success "Main info endpoint is working"
    else
        print_error "Main info endpoint failed"
        return 1
    fi
    
    # Test health endpoint
    if curl -f -s http://localhost:19999/api/v1/health > /dev/null 2>&1; then
        print_success "Health endpoint is working"
    else
        print_error "Health endpoint failed"
        return 1
    fi
    
    # Test charts endpoint
    if curl -f -s http://localhost:19999/api/v1/charts > /dev/null 2>&1; then
        print_success "Charts endpoint is working"
    else
        print_error "Charts endpoint failed"
        return 1
    fi
    
    # Test alarms endpoint
    if curl -f -s http://localhost:19999/api/v1/alarms > /dev/null 2>&1; then
        print_success "Alarms endpoint is working"
    else
        print_error "Alarms endpoint failed"
        return 1
    fi
}

# Test specific metrics
test_metrics() {
    print_status "Testing specific metrics..."
    
    # Test CPU metrics
    if curl -f -s "http://localhost:19999/api/v1/data?chart=system.cpu" > /dev/null 2>&1; then
        print_success "CPU metrics are available"
    else
        print_warning "CPU metrics not available"
    fi
    
    # Test memory metrics
    if curl -f -s "http://localhost:19999/api/v1/data?chart=system.ram" > /dev/null 2>&1; then
        print_success "Memory metrics are available"
    else
        print_warning "Memory metrics not available"
    fi
    
    # Test disk metrics
    if curl -f -s "http://localhost:19999/api/v1/data?chart=system.io" > /dev/null 2>&1; then
        print_success "Disk I/O metrics are available"
    else
        print_warning "Disk I/O metrics not available"
    fi
    
    # Test network metrics
    if curl -f -s "http://localhost:19999/api/v1/data?chart=system.net" > /dev/null 2>&1; then
        print_success "Network metrics are available"
    else
        print_warning "Network metrics not available"
    fi
}

# Test dashboard accessibility
test_dashboard_access() {
    print_status "Testing dashboard accessibility..."
    
    # Test main dashboard
    if curl -f -s http://localhost:19999 > /dev/null 2>&1; then
        print_success "Main dashboard is accessible"
    else
        print_error "Main dashboard is not accessible"
        return 1
    fi
    
    # Test dashboard API
    if curl -f -s http://localhost:19999/api/v1/info > /dev/null 2>&1; then
        print_success "Dashboard API is accessible"
    else
        print_error "Dashboard API is not accessible"
        return 1
    fi
}

# Display system information
display_system_info() {
    print_status "Displaying system information..."
    
    echo ""
    echo "=== Netdata System Information ==="
    curl -s http://localhost:19999/api/v1/info | head -20
    echo ""
    
    echo "=== Current Alarms ==="
    curl -s http://localhost:19999/api/v1/alarms | head -10
    echo ""
}

# Display access information
display_access_info() {
    print_status "Displaying access information..."
    
    echo ""
    echo "=== Netdata Dashboard Access ==="
    echo "Main Dashboard: http://localhost:19999"
    echo "API Info:       http://localhost:19999/api/v1/info"
    echo "Health Status:  http://localhost:19999/api/v1/health"
    echo "Charts Data:    http://localhost:19999/api/v1/charts"
    echo "Alarms:         http://localhost:19999/api/v1/alarms"
    echo ""
    
    echo "=== Service Management ==="
    echo "Check Status:   docker compose -f monitoring/netdata/docker-compose.simple.yml ps"
    echo "View Logs:      docker compose -f monitoring/netdata/docker-compose.simple.yml logs -f"
    echo "Stop Service:   docker compose -f monitoring/netdata/docker-compose.simple.yml down"
    echo "Restart:        docker compose -f monitoring/netdata/docker-compose.simple.yml restart"
    echo ""
}

# Main execution
main() {
    print_status "Starting Netdata Dashboard Test..."
    
    # Test API endpoints
    test_api_endpoints
    
    # Test metrics
    test_metrics
    
    # Test dashboard access
    test_dashboard_access
    
    # Display system information
    display_system_info
    
    # Display access information
    display_access_info
    
    print_success "Netdata Dashboard Test completed successfully!"
    print_status "Dashboard is accessible at: http://localhost:19999"
}

# Run main function
main "$@"
