#!/usr/bin/env bash
# status.sh — Show status of Digital Twin development services

set -uo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS_DIR="$DIR/.pids"
BACKEND_PID="$PIDS_DIR/backend.pid"
FRONTEND_PID="$PIDS_DIR/frontend.pid"
BACKEND_LOG="$DIR/logs/backend.log"
FRONTEND_LOG="$DIR/logs/frontend.log"

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

get_pid() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && cat "$pid_file" || echo "—"
}

port_open() {
  lsof -iTCP:"$1" -sTCP:LISTEN -n -P 2>/dev/null | grep -q LISTEN
}

health_check() {
  curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "$1" 2>/dev/null || echo "000"
}

show_log_tail() {
  local log="$1"
  local lines="${2:-5}"
  if [[ -f "$log" ]]; then
    echo -e "  ${DIM}Last $lines log lines:${NC}"
    tail -"$lines" "$log" | while IFS= read -r line; do
      echo -e "  ${DIM}│${NC} $line"
    done
  else
    echo -e "  ${DIM}│ (no log file yet)${NC}"
  fi
}

# ── Output ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║  Alex Rabinovich — Digital Twin Status       ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo -e "  ${DIM}$(date '+%A, %d %b %Y  %H:%M:%S')${NC}"

# ── Backend ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Backend  ${DIM}(FastAPI · uvicorn · port 8000)${NC}"
echo -e "  ─────────────────────────────────────────────"

if is_running "$BACKEND_PID"; then
  pid=$(get_pid "$BACKEND_PID")
  echo -e "  ${GREEN}●${NC} ${GREEN}${BOLD}Running${NC}   PID $pid   http://localhost:8000"

  # HTTP health check
  code=$(health_check "http://localhost:8000/health")
  if [[ "$code" == "200" ]]; then
    echo -e "  ${GREEN}✓${NC} Health check ${GREEN}OK${NC} (HTTP 200)"
  elif [[ "$code" == "000" ]]; then
    echo -e "  ${YELLOW}⚠${NC} Health check ${YELLOW}unreachable${NC} — process is up but not accepting connections yet"
  else
    echo -e "  ${YELLOW}⚠${NC} Health check returned ${YELLOW}HTTP $code${NC}"
  fi

  echo ""
  show_log_tail "$BACKEND_LOG" 6
else
  if [[ -f "$BACKEND_PID" ]]; then
    stale_pid=$(get_pid "$BACKEND_PID")
    echo -e "  ${RED}●${NC} ${RED}${BOLD}Crashed${NC}   PID $stale_pid no longer alive"
    rm -f "$BACKEND_PID"
  else
    echo -e "  ${RED}●${NC} ${BOLD}Stopped${NC}   (not started)"
  fi
  echo ""
  show_log_tail "$BACKEND_LOG" 6
fi

# ── Frontend ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Frontend  ${DIM}(Vite dev server · port 5173)${NC}"
echo -e "  ─────────────────────────────────────────────"

if is_running "$FRONTEND_PID"; then
  pid=$(get_pid "$FRONTEND_PID")
  echo -e "  ${GREEN}●${NC} ${GREEN}${BOLD}Running${NC}   PID $pid   http://localhost:5173"

  if port_open 5173; then
    echo -e "  ${GREEN}✓${NC} Port 5173 is open"
  else
    echo -e "  ${YELLOW}⚠${NC} Port 5173 not open yet — Vite may still be compiling"
  fi

  echo ""
  show_log_tail "$FRONTEND_LOG" 6
else
  if [[ -f "$FRONTEND_PID" ]]; then
    stale_pid=$(get_pid "$FRONTEND_PID")
    echo -e "  ${RED}●${NC} ${RED}${BOLD}Crashed${NC}   PID $stale_pid no longer alive"
    rm -f "$FRONTEND_PID"
  else
    echo -e "  ${RED}●${NC} ${BOLD}Stopped${NC}   (not started)"
  fi
  echo ""
  show_log_tail "$FRONTEND_LOG" 6
fi

# ── Quick Actions ─────────────────────────────────────────────────────────────
echo ""
echo -e "  ─────────────────────────────────────────────"
echo -e "  ${DIM}Quick actions:${NC}"
echo -e "  ${DIM}  ./start.sh                   Start services${NC}"
echo -e "  ${DIM}  ./start.sh --restart         Restart all${NC}"
echo -e "  ${DIM}  ./start.sh --rebuild         Resync deps and start${NC}"
echo -e "  ${DIM}  ./stop.sh                    Stop all services${NC}"
echo -e "  ${DIM}  tail -f logs/backend.log     Follow backend logs${NC}"
echo -e "  ${DIM}  tail -f logs/frontend.log    Follow frontend logs${NC}"
echo ""
