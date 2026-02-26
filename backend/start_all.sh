#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

compose_cmd() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

log() {
  echo "[start_all] $*"
}

local_postgres_running() {
  if ! command -v lsof >/dev/null 2>&1; then
    return 1
  fi
  lsof -nP -iTCP:5432 -sTCP:LISTEN 2>/dev/null | awk 'NR>1 && $1=="postgres"{found=1} END{exit !found}'
}

stop_local_postgres_service() {
  if command -v brew >/dev/null 2>&1; then
    while IFS= read -r svc; do
      [ -n "${svc}" ] || continue
      brew services stop "${svc}" >/dev/null 2>&1 || true
    done < <(brew services list 2>/dev/null | awk '$1 ~ /^postgresql/ && $2 == "started" {print $1}')
  fi
}

if [ -f "${REPO_ROOT}/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
fi

if [ -f "${SCRIPT_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env"
  set +a
fi

: "${POSTGRES_DB:=carpooling}"
: "${POSTGRES_USER:=carpool_user}"
: "${POSTGRES_PASSWORD:=change_me_postgres}"

# Single-command mode: always use Docker-managed infra endpoints.
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
export DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"
export REDIS_URL="redis://127.0.0.1:6379/0"
export KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:29092"
log "Using DB host ${POSTGRES_HOST}, Redis 127.0.0.1:6379, Kafka 127.0.0.1:29092"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not installed." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop and rerun ./start_all.sh." >&2
  exit 1
fi

if local_postgres_running; then
  log "Local Postgres detected on port 5432. Stopping local service so Docker Postgres can be used..."
  stop_local_postgres_service
  sleep 2
fi

if local_postgres_running; then
  echo "Local Postgres is still running on port 5432. Stop it and rerun ./start_all.sh." >&2
  exit 1
fi

log "Starting infrastructure containers (postgres, redis, zookeeper, kafka)..."
start_infra() {
  set +e
  compose_cmd up -d postgres redis zookeeper kafka
  infra_exit=$?
  set -e

  if [ "${infra_exit}" -eq 0 ]; then
    return 0
  fi

  # Typical local conflict: macOS Homebrew Postgres already owns 5432.
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:5432 -sTCP:LISTEN >/dev/null 2>&1; then
    log "Port 5432 is in use. Trying to stop local Postgres service and retry..."
    if command -v brew >/dev/null 2>&1; then
      while IFS= read -r svc; do
        [ -n "${svc}" ] || continue
        brew services stop "${svc}" >/dev/null 2>&1 || true
      done < <(brew services list 2>/dev/null | awk '$1 ~ /^postgresql/ && $2 == "started" {print $1}')
    fi
    sleep 2
    compose_cmd up -d postgres redis zookeeper kafka
    return 0
  fi

  return "${infra_exit}"
}

start_infra

wait_for() {
  local name="$1"
  local timeout="$2"
  shift 2
  local deadline=$((SECONDS + timeout))
  while [ "${SECONDS}" -lt "${deadline}" ]; do
    if "$@" >/dev/null 2>&1; then
      log "${name} is ready."
      return 0
    fi
    sleep 2
  done
  echo "Timed out waiting for ${name}." >&2
  return 1
}

check_postgres() {
  compose_cmd exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
}

check_redis() {
  [ "$(compose_cmd exec -T redis redis-cli ping 2>/dev/null | tr -d '\r')" = "PONG" ]
}

check_kafka() {
  compose_cmd exec -T kafka cub kafka-ready -b localhost:9092 1 20
}

wait_for postgres 180 check_postgres
wait_for redis 180 check_redis
wait_for kafka 240 check_kafka

TABLE_EXISTS="$(compose_cmd exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT to_regclass('public.outbox_events') IS NOT NULL;" 2>/dev/null | tr -d '[:space:]')"
if [ "${TABLE_EXISTS}" != "t" ]; then
  log "First-time setup detected. Initializing database schema..."
  compose_cmd exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /docker-entrypoint-initdb.d/init.sql >/dev/null
  log "Database schema initialized."
else
  log "Existing database schema detected."
fi

cd "${SCRIPT_DIR}"

PYTHON_BIN="python"
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if [ "${SKIP_DEPENDENCY_CHECK:-0}" != "1" ]; then
  "${PYTHON_BIN}" - <<'PY'
import os
import sys
import time
from sqlalchemy import create_engine, text
import redis
from confluent_kafka.admin import AdminClient

db_url = os.environ["DATABASE_URL"]
redis_url = os.environ["REDIS_URL"]
kafka_bootstrap = os.environ["KAFKA_BOOTSTRAP_SERVERS"]

deadline = time.time() + 180
last_error = "unknown"

while time.time() < deadline:
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        redis.Redis.from_url(redis_url).ping()

        admin = AdminClient({"bootstrap.servers": kafka_bootstrap})
        admin.list_topics(timeout=5)

        print("Dependencies are ready.")
        break
    except Exception as exc:  # noqa: BLE001
        last_error = str(exc)
        print(f"Waiting for dependencies: {last_error}")
        time.sleep(3)
else:
    print(f"Dependency check timed out: {last_error}", file=sys.stderr)
    sys.exit(1)
PY
fi

log "Starting outbox worker..."
"${PYTHON_BIN}" -m app.workers.outbox_processor &
OUTBOX_PID=$!

log "Starting booking consumer..."
"${PYTHON_BIN}" -m app.workers.booking_consumer &
CONSUMER_PID=$!

cleanup() {
  log "Stopping application processes..."
  for pid in "${API_PID:-}" "${OUTBOX_PID:-}" "${CONSUMER_PID:-}"; do
    if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup INT TERM EXIT

log "Starting API server..."
"${PYTHON_BIN}" -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" &
API_PID=$!

MONITORED_PIDS=("${API_PID}" "${OUTBOX_PID}" "${CONSUMER_PID}")

while true; do
  for pid in "${MONITORED_PIDS[@]}"; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      set +e
      wait "${pid}"
      exit_code=$?
      set -e
      cleanup
      exit "${exit_code}"
    fi
  done
  sleep 1
done
