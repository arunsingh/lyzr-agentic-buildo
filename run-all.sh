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

# Wait for a service in a compose file to reach healthy/up state
wait_health(){
	local svc="$1"; local file="$2"; local timeout="${3:-180}"; local t=0
	while :; do
		# Try docker compose ps --format json if jq exists
		if command -v jq >/dev/null 2>&1; then
			state=$(docker compose -f "$file" ps --format json 2>/dev/null | jq -r ".[] | select(.Service==\"$svc\") | .State" || true)
			[ -n "$state" ] || state=""
			if [[ "$state" =~ healthy|running ]]; then log_ok "$svc healthy"; return 0; fi
		else
			# Fallback to plain text parsing
			out=$(docker compose -f "$file" ps 2>/dev/null | awk -v s="$svc" '$0 ~ s {print $0}')
			if echo "$out" | grep -qiE "(healthy|Up)"; then log_ok "$svc healthy"; return 0; fi
		fi
		(( t++ >= timeout )) && { log_err "Timeout waiting for $svc"; docker compose -f "$file" ps || true; return 1; }
		sleep 1
	done
}

check_port_free(){ local port="$1"; if lsof -i ":$port" -sTCP:LISTEN -Pn >/dev/null 2>&1; then log_err "Port $port in use"; return 1; fi }

print_summary(){
	echo "\n==== Runtime Status Summary ===="
	echo "Core Infra ($DOCKER_DIR/docker-compose.yml):"; docker compose -f "$DOCKER_DIR/docker-compose.yml" ps || true
	echo "\nNetdata ($NETDATA_DIR/docker-compose.unified.yml):"; docker compose -f "$NETDATA_DIR/docker-compose.unified.yml" ps || true
	if [ -f "$MON_STACK" ]; then echo "\nMonitoring Stack:"; docker compose -f "$MON_STACK" ps || true; fi
	echo "\nHealth endpoints:"
	for u in \
		http://localhost:8000/health \
		http://localhost:8001/health \
		http://localhost:19999/api/v1/info \
		http://localhost:19998/api/v1/info; do
		if curl -fsS "$u" >/dev/null; then echo "[UP]   $u"; else echo "[DOWN] $u"; fi
	done
	echo "\nDashboards:"
	echo "Unified Netdata: http://localhost:19999"
	echo "API Netdata:     http://localhost:19998"
	echo "Worker Netdata:  http://localhost:19997"
	echo "Audit Netdata:   http://localhost:19996"
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

start_infra(){
	log_info "Starting Zookeeper"; docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d zookeeper; wait_health zookeeper "$DOCKER_DIR/docker-compose.yml" 120 || true
	log_info "Starting Kafka"; docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d kafka; wait_health kafka "$DOCKER_DIR/docker-compose.yml" 180 || true
	log_info "Starting Postgres, Redis, OPA, Keycloak"; docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d postgres redis opa keycloak
}

start_apps(){
	log_info "Starting core apps"
	docker compose -f "$DOCKER_DIR/docker-compose.yml" up -d audit api worker model_gateway tool_gateway tenant_manager session_service metering_service execution agent_registry
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
		docker compose -f "$NETDATA_DIR/docker-compose.unified.yml" down -v || true
		docker compose -f "$DOCKER_DIR/docker-compose.yml" down -v || true
		if [ -f "$MON_STACK" ]; then docker compose -f "$MON_STACK" down -v || true; fi
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
