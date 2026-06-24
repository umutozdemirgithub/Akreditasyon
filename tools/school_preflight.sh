#!/usr/bin/env bash
set -euo pipefail

PORT="${MEDEK_WEB_PORT:-8080}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass() { printf '[PASS] %s %s\n' "$1" "${2:-}"; }
fail() { printf '[FAIL] %s %s\n' "$1" "${2:-}"; }

echo "AKYS school server preflight"
echo "Project root: $ROOT"

if command -v docker >/dev/null 2>&1; then
  pass "Docker CLI" "$(docker --version)"
else
  fail "Docker CLI" "docker command not found"
fi

if docker compose version >/dev/null 2>&1; then
  pass "Docker Compose v2" "$(docker compose version)"
else
  fail "Docker Compose v2" "docker compose plugin not found"
fi

test -f docker-compose.web.yml && pass "docker-compose.web.yml" || fail "docker-compose.web.yml"
test -f Dockerfile.api && pass "Dockerfile.api" || fail "Dockerfile.api"
test -f frontend/Dockerfile && pass "frontend/Dockerfile" || fail "frontend/Dockerfile"
test -f .env && pass ".env file" || fail ".env file" "copy .env.web.example to .env"
test -d medek_data && pass "medek_data directory" || fail "medek_data directory"
test -f medek_data/medek_kys_v7_9.sqlite3 && pass "SQLite database" || fail "SQLite database"

if command -v ss >/dev/null 2>&1; then
  if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${PORT}$"; then
    fail "Port ${PORT} available" "port is already in use"
  else
    pass "Port ${PORT} available"
  fi
elif command -v netstat >/dev/null 2>&1; then
  if netstat -ltn | awk '{print $4}' | grep -Eq "[:.]${PORT}$"; then
    fail "Port ${PORT} available" "port is already in use"
  else
    pass "Port ${PORT} available"
  fi
else
  fail "Port check" "ss/netstat not found"
fi

echo
echo "Next command:"
echo "bash tools/start_web_stack.sh"

