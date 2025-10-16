#!/bin/bash

# AOB Platform Build and Deployment Automation
# This script handles building, testing, and deploying the AOB Platform

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
REGION="${2:-us-west-2}"
CLUSTER_NAME="aob-platform"

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
    
    # Check if required tools are installed
    local tools=("docker" "kubectl" "helm" "terraform" "node" "npm")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            print_error "$tool is not installed. Please install it and try again."
            exit 1
        fi
    done
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' and try again."
        exit 1
    fi
    
    print_success "All prerequisites are met"
}

# Function to build UI
build_ui() {
    print_status "Building UI application..."
    
    cd "$PROJECT_ROOT/ui"
    
    # Install dependencies
    print_status "Installing UI dependencies..."
    npm ci
    
    # Run type checking
    print_status "Running TypeScript type checking..."
    npm run type-check
    
    # Run linting
    print_status "Running ESLint..."
    npm run lint
    
    # Run tests
    print_status "Running tests..."
    npm run test
    
    # Build application
    print_status "Building application..."
    npm run build
    
    # Analyze bundle
    print_status "Analyzing bundle..."
    npm run analyze
    
    print_success "UI build completed"
}

# Function to build Docker images
build_docker_images() {
    print_status "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build API service
    print_status "Building API service image..."
    docker build -f docker/Dockerfile.api -t aob-api:latest .
    
    # Build Worker service
    print_status "Building Worker service image..."
    docker build -f docker/Dockerfile.worker -t aob-worker:latest .
    
    # Build Audit service
    print_status "Building Audit service image..."
    docker build -f docker/Dockerfile.audit_service -t aob-audit:latest .
    
    # Build Model Gateway
    print_status "Building Model Gateway image..."
    docker build -f docker/Dockerfile.model_gateway -t aob-model-gateway:latest .
    
    # Build Tool Gateway
    print_status "Building Tool Gateway image..."
    docker build -f docker/Dockerfile.tool_gateway -t aob-tool-gateway:latest .
    
    # Build Tenant Manager
    print_status "Building Tenant Manager image..."
    docker build -f docker/Dockerfile.tenant_manager -t aob-tenant-manager:latest .
    
    # Build Session Service
    print_status "Building Session Service image..."
    docker build -f docker/Dockerfile.session_service -t aob-session-service:latest .
    
    # Build Metering Service
    print_status "Building Metering Service image..."
    docker build -f docker/Dockerfile.metering_service -t aob-metering-service:latest .
    
    # Build Execution Service
    print_status "Building Execution Service image..."
    docker build -f docker/Dockerfile.execution_service -t aob-execution-service:latest .
    
    # Build Agent Registry
    print_status "Building Agent Registry image..."
    docker build -f docker/Dockerfile.agent_registry -t aob-agent-registry:latest .
    
    print_success "All Docker images built successfully"
}

# Function to run tests
run_tests() {
    print_status "Running comprehensive tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run unit tests
    print_status "Running unit tests..."
    npm run test --prefix ui
    
    # Run integration tests
    print_status "Running integration tests..."
    docker compose -f docker/docker-compose.yml up -d
    sleep 30
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    curl -f http://localhost:8000/health || print_warning "API health check failed"
    
    # Test Audit service
    print_status "Testing Audit service..."
    curl -f http://localhost:8001/health || print_warning "Audit service health check failed"
    
    # Cleanup
    docker compose -f docker/docker-compose.yml down
    
    print_success "Tests completed"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure for $ENVIRONMENT environment..."
    
    cd "$PROJECT_ROOT/terraform"
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var environment="$ENVIRONMENT" -var region="$REGION"
    
    # Apply deployment
    print_status "Applying Terraform deployment..."
    terraform apply -var environment="$ENVIRONMENT" -var region="$REGION" -auto-approve
    
    # Get outputs
    print_status "Getting Terraform outputs..."
    CLUSTER_NAME=$(terraform output -raw cluster_name)
    CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint)
    
    # Update kubeconfig
    print_status "Updating kubeconfig..."
    aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"
    
    print_success "Infrastructure deployed successfully"
}

# Function to deploy applications
deploy_applications() {
    print_status "Deploying applications to $ENVIRONMENT environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create namespace
    print_status "Creating namespace..."
    kubectl create namespace aob-platform --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy monitoring stack
    print_status "Deploying monitoring stack..."
    helm upgrade --install monitoring ./helm-charts/monitoring \
        --namespace aob-platform \
        --set environment="$ENVIRONMENT" \
        --wait
    
    # Deploy core services
    print_status "Deploying core services..."
    helm upgrade --install aob-core ./helm-charts/aob-core \
        --namespace aob-platform \
        --set environment="$ENVIRONMENT" \
        --wait
    
    # Deploy gateway services
    print_status "Deploying gateway services..."
    helm upgrade --install aob-gateways ./helm-charts/aob-gateways \
        --namespace aob-platform \
        --set environment="$ENVIRONMENT" \
        --wait
    
    # Deploy UI
    print_status "Deploying UI..."
    helm upgrade --install aob-ui ./helm-charts/aob-ui \
        --namespace aob-platform \
        --set environment="$ENVIRONMENT" \
        --wait
    
    print_success "Applications deployed successfully"
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check cluster status
    print_status "Checking cluster status..."
    kubectl get nodes
    
    # Check pod status
    print_status "Checking pod status..."
    kubectl get pods -n aob-platform
    
    # Check service status
    print_status "Checking service status..."
    kubectl get services -n aob-platform
    
    # Check ingress status
    print_status "Checking ingress status..."
    kubectl get ingress -n aob-platform
    
    print_success "Health checks completed"
}

# Function to run performance tests
run_performance_tests() {
    print_status "Running performance tests..."
    
    cd "$PROJECT_ROOT"
    
    # Install k6 if not present
    if ! command -v k6 &> /dev/null; then
        print_status "Installing k6..."
        brew install k6
    fi
    
    # Run load tests
    print_status "Running load tests..."
    k6 run tests/performance/load-test.js
    
    # Run stress tests
    print_status "Running stress tests..."
    k6 run tests/performance/stress-test.js
    
    print_success "Performance tests completed"
}

# Function to run security scans
run_security_scans() {
    print_status "Running security scans..."
    
    cd "$PROJECT_ROOT"
    
    # Install Trivy if not present
    if ! command -v trivy &> /dev/null; then
        print_status "Installing Trivy..."
        brew install trivy
    fi
    
    # Scan Docker images
    print_status "Scanning Docker images..."
    trivy image aob-api:latest
    trivy image aob-worker:latest
    trivy image aob-audit:latest
    
    # Scan Kubernetes manifests
    print_status "Scanning Kubernetes manifests..."
    trivy k8s cluster --namespace aob-platform
    
    print_success "Security scans completed"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up..."
    
    cd "$PROJECT_ROOT"
    
    # Stop Docker Compose
    docker compose -f docker/docker-compose.yml down -v
    
    # Clean Docker images
    docker system prune -f
    
    print_success "Cleanup completed"
}

# Function to show help
show_help() {
    echo "AOB Platform Build and Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [ENVIRONMENT] [REGION]"
    echo ""
    echo "Commands:"
    echo "  build-ui          Build UI application"
    echo "  build-docker      Build Docker images"
    echo "  test              Run tests"
    echo "  deploy-infra      Deploy infrastructure"
    echo "  deploy-apps       Deploy applications"
    echo "  health-check      Run health checks"
    echo "  perf-test         Run performance tests"
    echo "  security-scan     Run security scans"
    echo "  cleanup           Cleanup resources"
    echo "  all               Run all steps"
    echo ""
    echo "Environments:"
    echo "  dev               Development environment"
    echo "  staging           Staging environment"
    echo "  prod              Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 build-ui"
    echo "  $0 deploy-infra dev us-west-2"
    echo "  $0 all prod us-east-1"
}

# Main execution
main() {
    local command="${1:-all}"
    local environment="${2:-dev}"
    local region="${3:-us-west-2}"
    
    case "$command" in
        "build-ui")
            check_prerequisites
            build_ui
            ;;
        "build-docker")
            check_prerequisites
            build_docker_images
            ;;
        "test")
            check_prerequisites
            run_tests
            ;;
        "deploy-infra")
            check_prerequisites
            deploy_infrastructure
            ;;
        "deploy-apps")
            check_prerequisites
            deploy_applications
            ;;
        "health-check")
            check_prerequisites
            run_health_checks
            ;;
        "perf-test")
            check_prerequisites
            run_performance_tests
            ;;
        "security-scan")
            check_prerequisites
            run_security_scans
            ;;
        "cleanup")
            cleanup
            ;;
        "all")
            check_prerequisites
            build_ui
            build_docker_images
            run_tests
            deploy_infrastructure
            deploy_applications
            run_health_checks
            run_performance_tests
            run_security_scans
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
