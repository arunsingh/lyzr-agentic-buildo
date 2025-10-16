#!/bin/bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$ROOT_DIR/docker"
NETDATA_DIR="$ROOT_DIR/monitoring/netdata"
MON_STACK="$ROOT_DIR/monitoring/docker-compose.monitoring.yml"

log_info(){ echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok(){ echo -e "${GREEN}[OK]${NC} $1"; }
log_warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err(){ echo -e "${RED}[ERR]${NC} $1"; }

need(){ command -v "$1" >/dev/null 2>&1 || { log_err "$1 not found"; exit 1; }; }

# Generic retry wrapper for flaky operations (e.g., image pulls/builds)
retry(){
    local attempts="${1:-3}"; shift
    local delay="${1:-5}"; shift
    local n=1
    while :; do
        "$@" && return 0 || true
        if [ $n -ge $attempts ]; then
            return 1
        fi
        log_warn "retry $n/$attempts failed: $*; sleeping ${delay}s"
        sleep "$delay"
        n=$((n+1))
    done
}

# Run a command with a soft timeout; if exceeded, kill it and return non-zero
run_with_timeout(){
    local timeout_sec="$1"; shift
    local desc="$1"; shift
    log_info "${desc} (timeout=${timeout_sec}s)"
    ( "$@" ) &
    local cmd_pid=$!
    local elapsed=0
    while kill -0 $cmd_pid >/dev/null 2>&1; do
        sleep 1
        elapsed=$((elapsed+1))
        if [ $elapsed -ge $timeout_sec ]; then
            log_warn "Timeout reached for: ${desc}; sending SIGKILL"
            kill -9 $cmd_pid >/dev/null 2>&1 || true
            wait $cmd_pid >/dev/null 2>&1 || true
            return 124
        fi
    done
    wait $cmd_pid
    return $?
}

# Wait for a service in a compose file to reach healthy/up state
wait_health(){
    local svc="$1"; local file="$2"; local timeout="${3:-180}"; local t=0
    while :; do
        local ok=""
        if command -v jq >/dev/null 2>&1; then
            # Some compose versions return non-JSON; guard and fallback
            local json
            json=$(docker compose -f "$file" ps --format json 2>/dev/null || true)
            if echo "$json" | grep -q "^\["; then
                state=$(echo "$json" | jq -r ".[] | select(.Service==\"$svc\") | .State" 2>/dev/null || true)
                if [[ "$state" =~ healthy|running ]]; then ok="yes"; fi
            fi
        fi
        if [ -z "$ok" ]; then
            # Fallback to plain text parsing
            out=$(docker compose -f "$file" ps 2>/dev/null | awk -v s="$svc" '$0 ~ s {print $0}')
            if echo "$out" | grep -qiE "(healthy|Up)"; then ok="yes"; fi
        fi
        if [ "$ok" = "yes" ]; then log_ok "$svc healthy"; return 0; fi
        (( t++ >= timeout )) && { log_err "Timeout waiting for $svc"; docker compose -f "$file" ps || true; return 1; }
        sleep 1
    done
}

check_port_free(){ local port="$1"; if lsof -i ":$port" -sTCP:LISTEN -Pn >/dev/null 2>&1; then log_err "Port $port in use"; return 1; fi }

print_summary(){
    # Don't abort on failures in status printing
    set +e
    echo "\n==== Runtime Status Summary ===="
    echo "Core Infra ($DOCKER_DIR/docker-compose.yml):"
    docker compose -f "$DOCKER_DIR/docker-compose.yml" ps 2>/dev/null || echo "(compose unavailable or stack not running)"

    echo "\nNetdata ($NETDATA_DIR/docker-compose.unified.yml):"
    docker compose -f "$NETDATA_DIR/docker-compose.unified.yml" ps 2>/dev/null || echo "(compose unavailable or stack not running)"

    if [ -f "$MON_STACK" ]; then
        echo "\nMonitoring Stack ($MON_STACK):"
        docker compose -f "$MON_STACK" ps 2>/dev/null || echo "(compose unavailable or stack not running)"
    fi

    echo "\nHealth endpoints:"
    for u in \
        http://localhost:8000/health \
        http://localhost:8001/health \
        http://localhost:19999/api/v1/info \
        http://localhost:19998/api/v1/info; do
        if command -v curl >/dev/null 2>&1; then
            if curl -fsS "$u" >/dev/null; then echo "[UP]   $u"; else echo "[DOWN] $u"; fi
        else
            echo "[SKIP] curl not installed for $u"
        fi
    done

    echo "\nDashboards:"
    echo "Unified Netdata: http://localhost:19999"
    echo "API Netdata:     http://localhost:19998"
    echo "Worker Netdata:  http://localhost:19997"
    echo "Audit Netdata:   http://localhost:19996"
    # Restore error handling
    set -e
}

pre_checks(){
	log_info "Pre-run checklist"
	need docker; need curl; docker compose version >/dev/null || { log_err "docker compose unavailable"; exit 1; }
	# Free up common ports or stop conflicting stacks
	for p in 8000 8001 19999 19998 19997 19996 19995 19994 19993 19992 19991 19990 19989 55432 6379 2181 9092; do
		if ! check_port_free "$p"; then
			log_warn "Port $p busy; attempting graceful stop of known stacks"
			docker compose -f "$NETDATA_DIR/docker-compose.simple.yml" down -v >/dev/null 2>&1 || true
			docker compose -f "$NETDATA_DIR/docker-compose.unified.yml" down -v >/dev/null 2>&1 || true
			docker compose -f "$DOCKER_DIR/docker-compose.yml" down >/dev/null 2>&1 || true
		fi
	done
	# Ensure network
	docker network inspect aob-network >/dev/null 2>&1 || docker network create aob-network >/dev/null
	log_ok "Pre-checks complete"
}

pre_pull_images(){
    log_info "Pre-pulling common images to reduce build time"
    retry 3 5 docker pull confluentinc/cp-zookeeper:7.6.1 >/dev/null 2>&1 || true
    retry 3 5 docker pull confluentinc/cp-kafka:7.6.1 >/dev/null 2>&1 || true
    retry 3 5 docker pull qdrant/qdrant:latest >/dev/null 2>&1 || true
}

start_infra(){
	log_info "Starting Zookeeper"; docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d zookeeper; wait_health zookeeper "$DOCKER_DIR/docker-compose.yml" 120 || true
	log_info "Starting Kafka"; docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d kafka; wait_health kafka "$DOCKER_DIR/docker-compose.yml" 180 || true
	log_info "Starting Postgres, Redis, OPA, Keycloak"; docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d postgres redis opa keycloak
}

start_apps(){
	log_info "Starting core apps"
    has_service(){
        docker compose -f "$DOCKER_DIR/docker-compose.yml" config --services 2>/dev/null | awk -v s="$1" '$0==s {found=1} END{exit found?0:1}'
    }
    # Desired services in approximate dependency order
    desired_services=(
        audit api worker model_gateway tool_gateway tenant_manager session_service metering execution agent_registry qdrant qdrant_rag
    )
    # Build list of existing services
    existing=()
    for s in "${desired_services[@]}"; do
        if has_service "$s"; then
            existing+=("$s")
        else
            log_warn "Service '$s' not present in compose, skipping"
        fi
    done
    if [ ${#existing[@]} -gt 0 ]; then
        # Enable BuildKit for faster/more reliable builds
        export DOCKER_BUILDKIT=1
        export COMPOSE_DOCKER_CLI_BUILD=1
        # Optionally enable bake if user sets COMPOSE_BAKE=true
        if [ "${COMPOSE_BAKE:-}" = "true" ]; then
            log_info "Using compose bake for builds (COMPOSE_BAKE=true)"
        fi
        # Build services with retry to handle transient network/EOF during pip install
        log_info "Building application services (with retry)"
        retry 2 10 docker compose -f "$DOCKER_DIR/docker-compose.yml" build --pull "${existing[@]}" || {
            log_warn "Build failed once; retrying with no-cache for problematic layers"
            retry 1 10 docker compose -f "$DOCKER_DIR/docker-compose.yml" build --pull --no-cache "${existing[@]}" || true
        }
        docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d "${existing[@]}"
    else
        log_warn "No application services found to start in compose file"
    fi
}

start_monitoring(){
	log_info "Stopping standalone Netdata if running"; docker compose -f "$NETDATA_DIR/docker-compose.simple.yml" down >/dev/null 2>&1 || true
	log_info "Starting unified Netdata"
	docker compose -f "$NETDATA_DIR/docker-compose.unified.yml" up -d
}

post_checks(){
	log_info "Running post-run checks"
	sleep 10
	print_summary
}

case "${1:-up}" in
	up)
		pre_checks
		start_infra
		start_apps
		start_monitoring
		post_checks
		;;
	down)
		log_info "Stopping all stacks"
		# Try graceful down first (with remove-orphans and explicit stop timeout)
		run_with_timeout 120 "netdata down" docker compose -f "$NETDATA_DIR/docker-compose.unified.yml" down -v --remove-orphans --timeout 10 || true
		run_with_timeout 120 "core down" docker compose -f "$DOCKER_DIR/docker-compose.yml" down -v --remove-orphans --timeout 10 || true
		if [ -f "$MON_STACK" ]; then run_with_timeout 90 "monitoring down" docker compose -f "$MON_STACK" down -v --remove-orphans --timeout 10 || true; fi

		# Handle zombie containers: force kill/remove by compose project label
		force_stop_project(){
			local project="$1"
			# Kill any remaining containers for the project
			ids=$(docker ps -aq --filter "label=com.docker.compose.project=$project") || true
			if [ -n "$ids" ]; then
				log_warn "Forcing stop/remove for project=$project (possible zombie PIDs)"
				# try stop with SIGKILL
				docker kill -s SIGKILL $ids >/dev/null 2>&1 || true
				docker rm -f $ids >/dev/null 2>&1 || true
			fi
		}

		# Known compose projects
		force_stop_project "netdata"
		force_stop_project "docker"
		force_stop_project "monitoring"

		# Prune any dangling resources
		log_info "Pruning dangling containers and networks"
		docker container prune -f >/dev/null 2>&1 || true
		docker network prune -f >/dev/null 2>&1 || true
		log_ok "All stopped"
		;;
	status)
		print_summary
		;;
	restart)
		"$0" down && "$0" up
		;;
	*)
		echo "Usage: $0 {up|down|status|restart}"; exit 1;
		;;
esac
