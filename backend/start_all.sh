#!/usr/bin/env bash
set -euo pipefail

cd /app/backend

python - <<'PY'
import os
import sys
import time
from sqlalchemy import create_engine, text
import redis
from confluent_kafka import AdminClient

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

python -m app.workers.outbox_processor &
OUTBOX_PID=$!

python -m app.workers.booking_consumer &
CONSUMER_PID=$!

cleanup() {
  kill "${API_PID:-}" "${OUTBOX_PID}" "${CONSUMER_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

wait -n "${API_PID}" "${OUTBOX_PID}" "${CONSUMER_PID}"
exit_code=$?
cleanup
exit "${exit_code}"
