#!/usr/bin/env bash
# stop.sh — Stop all Digital Twin development services

set -uo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS_DIR="$DIR/.pids"
BACKEND_PID="$PIDS_DIR/backend.pid"
FRONTEND_PID="$PIDS_DIR/frontend.pid"

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ts()   { date '+%H:%M:%S'; }
info() { echo -e "${DIM}[$(ts)]${NC} ${CYAN}ℹ${NC}  $*"; }
ok()   { echo -e "${DIM}[$(ts)]${NC} ${GREEN}✓${NC}  $*"; }
warn() { echo -e "${DIM}[$(ts)]${NC} ${YELLOW}⚠${NC}  $*"; }

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  if is_running "$pid_file"; then
    local pid
    pid=$(cat "$pid_file")
    info "Stopping $name (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    # Wait up to 5 s for graceful shutdown
    local i=0
    while kill -0 "$pid" 2>/dev/null && [[ $i -lt 10 ]]; do
      sleep 0.5
      i=$((i + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      warn "$name didn't stop gracefully — force-killing..."
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
    ok "$name stopped"
  else
    warn "$name is not running"
    rm -f "$pid_file" 2>/dev/null || true
  fi
}

echo ""
echo -e "${BOLD}${CYAN}Stopping Digital Twin services...${NC}"
echo ""

stop_service "Backend"  "$BACKEND_PID"
stop_service "Frontend" "$FRONTEND_PID"

echo ""
ok "Done"
echo ""
