#!/usr/bin/env bash
# start.sh — Start the Digital Twin chatbot development environment
#
# Usage:
#   ./start.sh                          Start both services (skip if already running)
#   ./start.sh --rebuild                Re-sync Python deps + npm packages, then start
#   ./start.sh --rebuild backend        Re-sync Python deps only
#   ./start.sh --rebuild frontend       Re-install npm packages only
#   ./start.sh --restart                Stop and restart both services
#   ./start.sh --restart backend        Stop and restart backend only
#   ./start.sh --restart frontend       Stop and restart frontend only
#   ./start.sh --rebuild --restart      Rebuild all deps, then restart both services
#   ./start.sh -h, --help               Show this help

set -uo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS_DIR="$DIR/.pids"
LOGS_DIR="$DIR/logs"
BACKEND_PID="$PIDS_DIR/backend.pid"
FRONTEND_PID="$PIDS_DIR/frontend.pid"
BACKEND_LOG="$LOGS_DIR/backend.log"
FRONTEND_LOG="$LOGS_DIR/frontend.log"

mkdir -p "$PIDS_DIR" "$LOGS_DIR"

NPM_CMD="npm"  # may be overridden in preflight if npm isn't directly in PATH

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Logging ───────────────────────────────────────────────────────────────────
ts()   { date '+%H:%M:%S'; }
info() { echo -e "${DIM}[$(ts)]${NC} ${CYAN}ℹ${NC}  $*"; }
ok()   { echo -e "${DIM}[$(ts)]${NC} ${GREEN}✓${NC}  $*"; }
warn() { echo -e "${DIM}[$(ts)]${NC} ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${DIM}[$(ts)]${NC} ${RED}✗${NC}  $*" >&2; }
step() { echo -e "\n${BOLD}${CYAN}▶ $*${NC}"; }

banner() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${CYAN}║  Alex Rabinovich — Digital Twin Chatbot      ║${NC}"
  echo -e "${BOLD}${CYAN}║  Development Environment                     ║${NC}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── PID Helpers ───────────────────────────────────────────────────────────────
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
    info "$name is not running"
    rm -f "$pid_file" 2>/dev/null || true
  fi
}

# ── Rebuild Helpers ───────────────────────────────────────────────────────────
rebuild_backend() {
  step "Rebuilding backend — syncing Python dependencies"
  info "Running: uv sync"
  cd "$DIR"
  if uv sync; then
    ok "Python dependencies synced"
  else
    err "uv sync failed — aborting"
    exit 1
  fi
}

rebuild_frontend() {
  step "Rebuilding frontend — installing npm packages"
  info "Running: npm install  (in frontend/)"
  cd "$DIR/frontend"
  if $NPM_CMD install; then
    ok "npm packages installed"
  else
    err "npm install failed — aborting"
    exit 1
  fi
  cd "$DIR"
}

# ── Start Helpers ─────────────────────────────────────────────────────────────
start_backend() {
  if is_running "$BACKEND_PID"; then
    warn "Backend is already running (PID $(cat "$BACKEND_PID")) — skipping"
    warn "Use --restart backend to force a restart"
    return 0
  fi
  step "Starting backend"
  info "Command: uv run uvicorn backend.main:app --reload --port 8000"
  info "Log:     $BACKEND_LOG"
  cd "$DIR"
  {
    echo ""
    echo "=== Backend started at $(date) ==="
  } >> "$BACKEND_LOG"
  uv run uvicorn backend.main:app --reload --port 8000 >> "$BACKEND_LOG" 2>&1 &
  local pid=$!
  echo "$pid" > "$BACKEND_PID"
  info "Backend PID: $pid"
  # Give it a moment to start (or fail)
  sleep 2
  if is_running "$BACKEND_PID"; then
    ok "Backend running → http://localhost:8000"
  else
    err "Backend failed to start"
    err "Check logs: tail -f $BACKEND_LOG"
    rm -f "$BACKEND_PID"
    exit 1
  fi
}

start_frontend() {
  if is_running "$FRONTEND_PID"; then
    warn "Frontend is already running (PID $(cat "$FRONTEND_PID")) — skipping"
    warn "Use --restart frontend to force a restart"
    return 0
  fi
  step "Starting frontend"
  info "Command: npm run dev  (in frontend/)"
  info "Log:     $FRONTEND_LOG"
  cd "$DIR/frontend"
  {
    echo ""
    echo "=== Frontend started at $(date) ==="
  } >> "$FRONTEND_LOG"
  $NPM_CMD run dev >> "$FRONTEND_LOG" 2>&1 &
  local pid=$!
  echo "$pid" > "$FRONTEND_PID"
  cd "$DIR"
  info "Frontend PID: $pid"
  # Vite needs a moment to compile
  sleep 3
  if is_running "$FRONTEND_PID"; then
    ok "Frontend running → http://localhost:5173"
  else
    err "Frontend failed to start"
    err "Check logs: tail -f $FRONTEND_LOG"
    rm -f "$FRONTEND_PID"
    exit 1
  fi
}

# ── Argument Parsing ──────────────────────────────────────────────────────────
REBUILD_ALL=false
REBUILD_BACKEND=false
REBUILD_FRONTEND=false
RESTART_ALL=false
RESTART_BACKEND=false
RESTART_FRONTEND=false

show_help() {
  echo ""
  echo -e "${BOLD}Usage:${NC}"
  echo "  ./start.sh                          Start both services (skip if already running)"
  echo "  ./start.sh --rebuild                Re-sync Python deps + npm packages, then start"
  echo "  ./start.sh --rebuild backend        Re-sync Python deps only"
  echo "  ./start.sh --rebuild frontend       Re-install npm packages only"
  echo "  ./start.sh --restart                Stop and restart both services"
  echo "  ./start.sh --restart backend        Stop and restart backend only"
  echo "  ./start.sh --restart frontend       Stop and restart frontend only"
  echo "  ./start.sh --rebuild --restart      Rebuild all deps, then restart both"
  echo ""
  echo -e "${BOLD}Examples:${NC}"
  echo "  ./start.sh --rebuild backend --restart backend   Resync deps and bounce backend"
  echo "  ./start.sh --rebuild --restart                   Full clean restart with dep sync"
  echo ""
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rebuild)
      if [[ "${2:-}" == "backend" ]];  then REBUILD_BACKEND=true;  shift
      elif [[ "${2:-}" == "frontend" ]]; then REBUILD_FRONTEND=true; shift
      else REBUILD_ALL=true
      fi
      shift ;;
    --restart)
      if [[ "${2:-}" == "backend" ]];  then RESTART_BACKEND=true;  shift
      elif [[ "${2:-}" == "frontend" ]]; then RESTART_FRONTEND=true; shift
      else RESTART_ALL=true
      fi
      shift ;;
    --help|-h)
      banner
      show_help
      exit 0 ;;
    *)
      err "Unknown option: $1"
      show_help
      exit 1 ;;
  esac
done

# ── Pre-flight Checks ─────────────────────────────────────────────────────────
preflight() {
  step "Pre-flight checks"
  local all_ok=true

  if command -v uv &>/dev/null; then
    ok "uv $(uv --version 2>/dev/null | head -1)"
  else
    err "uv not found — install from https://docs.astral.sh/uv/"
    all_ok=false
  fi

  if command -v node &>/dev/null; then
    ok "node $(node --version)"
  else
    err "node not found — install Node.js 20+"
    all_ok=false
  fi

  if command -v npm &>/dev/null; then
    ok "npm $(npm --version 2>/dev/null | head -1)"
  elif command -v node &>/dev/null && [[ -e "$(dirname "$(command -v node)")/npm" ]]; then
    NPM_CMD="$(dirname "$(command -v node)")/npm"
    ok "npm $($NPM_CMD --version 2>/dev/null | head -1) (at $NPM_CMD)"
  else
    err "npm not found — reinstall Node.js 20+"
    all_ok=false
  fi

  if [[ ! -f "$DIR/.env" ]]; then
    err ".env not found — create one with OPENAI_API_KEY=sk-..."
    all_ok=false
  elif ! grep -q "OPENAI_API_KEY" "$DIR/.env"; then
    warn ".env exists but OPENAI_API_KEY not found in it"
  else
    ok ".env found with OPENAI_API_KEY"
  fi

  if [[ ! -d "$DIR/frontend/node_modules" ]]; then
    warn "frontend/node_modules missing — run with --rebuild (or --rebuild frontend)"
  fi

  [[ "$all_ok" == "true" ]] || exit 1
}

# ── Main ──────────────────────────────────────────────────────────────────────
banner
preflight

# Determine which services to operate on
DO_BACKEND=false
DO_FRONTEND=false

$REBUILD_ALL   && { DO_BACKEND=true; DO_FRONTEND=true; }
$RESTART_ALL   && { DO_BACKEND=true; DO_FRONTEND=true; }
$REBUILD_BACKEND  && DO_BACKEND=true
$REBUILD_FRONTEND && DO_FRONTEND=true
$RESTART_BACKEND  && DO_BACKEND=true
$RESTART_FRONTEND && DO_FRONTEND=true

# No specific flags → operate on both
if ! $DO_BACKEND && ! $DO_FRONTEND; then
  DO_BACKEND=true
  DO_FRONTEND=true
fi

# ── Backend ───────────────────────────────────────────────────────────────────
if $DO_BACKEND; then
  if $REBUILD_ALL || $REBUILD_BACKEND; then
    rebuild_backend
  fi
  if $RESTART_ALL || $RESTART_BACKEND; then
    stop_service "Backend" "$BACKEND_PID"
  fi
  start_backend
fi

# ── Frontend ──────────────────────────────────────────────────────────────────
if $DO_FRONTEND; then
  if $REBUILD_ALL || $REBUILD_FRONTEND; then
    rebuild_frontend
  fi
  if $RESTART_ALL || $RESTART_FRONTEND; then
    stop_service "Frontend" "$FRONTEND_PID"
  fi
  start_frontend
fi

# ── Summary ───────────────────────────────────────────────────────────────────
step "Ready"
echo ""
echo -e "  ${BOLD}Backend:${NC}   ${GREEN}http://localhost:8000${NC}  ${DIM}(FastAPI + auto-reload)${NC}"
echo -e "  ${BOLD}Frontend:${NC}  ${GREEN}http://localhost:5173${NC}  ${DIM}(Vite dev server)${NC}"
echo ""
echo -e "  ${DIM}Follow logs:${NC}"
echo -e "    tail -f $BACKEND_LOG"
echo -e "    tail -f $FRONTEND_LOG"
echo ""
echo -e "  ${DIM}Controls:${NC}"
echo -e "    ./status.sh      Show service status and recent logs"
echo -e "    ./stop.sh        Stop all services"
echo ""
