#!/bin/bash

# AOB Platform Unified Monitoring Dashboard Setup
# This script sets up the complete monitoring infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT="${1:-dev}"

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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please install Docker Compose and try again."
        exit 1
    fi
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js and try again."
        exit 1
    fi
    
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm and try again."
        exit 1
    fi
    
    print_success "All prerequisites are met"
}

# Function to start unified Netdata monitoring
start_unified_monitoring() {
    print_status "Starting unified Netdata monitoring..."
    
    cd "$PROJECT_ROOT/monitoring/netdata"
    
    # Start unified Netdata services
    docker compose -f docker-compose.unified.yml up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check service status
    print_status "Checking service status..."
    docker compose -f docker-compose.unified.yml ps
    
    print_success "Unified Netdata monitoring started"
}

# Function to start AOB Platform services
start_aob_services() {
    print_status "Starting AOB Platform services..."
    
    cd "$PROJECT_ROOT/docker"
    
    # Start core services
    docker compose up -d postgres redis kafka zookeeper opa keycloak
    
    # Wait for core services
    print_status "Waiting for core services..."
    sleep 60
    
    # Start application services
    docker compose up -d api worker audit
    
    # Wait for application services
    print_status "Waiting for application services..."
    sleep 30
    
    # Check service status
    print_status "Checking service status..."
    docker compose ps
    
    print_success "AOB Platform services started"
}

# Function to build and start UI
start_ui() {
    print_status "Building and starting UI..."
    
    cd "$PROJECT_ROOT/ui"
    
    # Install dependencies
    print_status "Installing UI dependencies..."
    npm ci
    
    # Build application
    print_status "Building application..."
    npm run build
    
    # Start development server
    print_status "Starting development server..."
    npm run dev &
    
    # Wait for UI to start
    sleep 10
    
    print_success "UI started successfully"
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check Netdata services
    print_status "Checking Netdata services..."
    curl -f http://localhost:19999/api/v1/info || print_warning "Main Netdata not responding"
    curl -f http://localhost:19998/api/v1/info || print_warning "API Netdata not responding"
    curl -f http://localhost:19997/api/v1/info || print_warning "Worker Netdata not responding"
    curl -f http://localhost:19996/api/v1/info || print_warning "Audit Netdata not responding"
    
    # Check AOB services
    print_status "Checking AOB services..."
    curl -f http://localhost:8000/health || print_warning "API service not responding"
    curl -f http://localhost:8001/health || print_warning "Audit service not responding"
    
    # Check UI
    print_status "Checking UI..."
    curl -f http://localhost:5173 || print_warning "UI not responding"
    
    print_success "Health checks completed"
}

# Function to display access information
display_access_info() {
    print_status "Displaying access information..."
    
    echo ""
    echo "=== AOB Platform Unified Monitoring Dashboard ==="
    echo ""
    echo "Main Unified Dashboard: http://localhost:19999"
    echo "UI Application:         http://localhost:5173"
    echo "API Service:            http://localhost:8000"
    echo "Audit Service:          http://localhost:8001"
    echo ""
    echo "=== Service-Specific Dashboards ==="
    echo "API Service:            http://localhost:19998"
    echo "Worker Service:         http://localhost:19997"
    echo "Audit Service:          http://localhost:19996"
    echo "Model Gateway:          http://localhost:19995"
    echo "Tool Gateway:           http://localhost:19994"
    echo "Tenant Manager:         http://localhost:19993"
    echo "Session Service:        http://localhost:19992"
    echo "Metering Service:       http://localhost:19991"
    echo "Execution Service:      http://localhost:19990"
    echo "Agent Registry:         http://localhost:19989"
    echo ""
    echo "=== Management Commands ==="
    echo "Check Status:           docker compose -f monitoring/netdata/docker-compose.unified.yml ps"
    echo "View Logs:              docker compose -f monitoring/netdata/docker-compose.unified.yml logs -f"
    echo "Stop Services:          docker compose -f monitoring/netdata/docker-compose.unified.yml down"
    echo "Restart Services:       docker compose -f monitoring/netdata/docker-compose.unified.yml restart"
    echo ""
    echo "=== UI Development ==="
    echo "Start Dev Server:       cd ui && npm run dev"
    echo "Build Production:       cd ui && npm run build"
    echo "Run Tests:              cd ui && npm run test"
    echo "Run Linting:            cd ui && npm run lint"
    echo ""
}

# Function to run performance tests
run_performance_tests() {
    print_status "Running performance tests..."
    
    cd "$PROJECT_ROOT"
    
    # Test Netdata performance
    print_status "Testing Netdata performance..."
    for port in 19999 19998 19997 19996; do
        echo "Testing port $port..."
        curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:$port/api/v1/info" || print_warning "Port $port not responding"
    done
    
    # Test API performance
    print_status "Testing API performance..."
    curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/health" || print_warning "API not responding"
    
    # Test UI performance
    print_status "Testing UI performance..."
    curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:5173" || print_warning "UI not responding"
    
    print_success "Performance tests completed"
}

# Function to create curl format file
create_curl_format() {
    print_status "Creating curl format file..."
    
    cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
    
    print_success "Curl format file created"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up..."
    
    cd "$PROJECT_ROOT"
    
    # Stop Netdata services
    print_status "Stopping Netdata services..."
    docker compose -f monitoring/netdata/docker-compose.unified.yml down -v
    
    # Stop AOB services
    print_status "Stopping AOB services..."
    docker compose -f docker/docker-compose.yml down -v
    
    # Clean Docker images
    print_status "Cleaning Docker images..."
    docker system prune -f
    
    print_success "Cleanup completed"
}

# Function to show help
show_help() {
    echo "AOB Platform Unified Monitoring Dashboard Setup"
    echo ""
    echo "Usage: $0 [COMMAND] [ENVIRONMENT]"
    echo ""
    echo "Commands:"
    echo "  start-monitoring    Start unified Netdata monitoring"
    echo "  start-services      Start AOB Platform services"
    echo "  start-ui           Build and start UI"
    echo "  health-check       Run health checks"
    echo "  perf-test          Run performance tests"
    echo "  cleanup            Cleanup resources"
    echo "  all                Run all setup steps"
    echo ""
    echo "Environments:"
    echo "  dev                Development environment"
    echo "  staging            Staging environment"
    echo "  prod               Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 start-monitoring"
    echo "  $0 all dev"
    echo "  $0 health-check"
}

# Main execution
main() {
    local command="${1:-all}"
    local environment="${2:-dev}"
    
    case "$command" in
        "start-monitoring")
            check_prerequisites
            start_unified_monitoring
            ;;
        "start-services")
            check_prerequisites
            start_aob_services
            ;;
        "start-ui")
            check_prerequisites
            start_ui
            ;;
        "health-check")
            run_health_checks
            ;;
        "perf-test")
            create_curl_format
            run_performance_tests
            ;;
        "cleanup")
            cleanup
            ;;
        "all")
            check_prerequisites
            create_curl_format
            start_unified_monitoring
            start_aob_services
            start_ui
            run_health_checks
            run_performance_tests
            display_access_info
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
