#!/bin/bash
# Test runner script for carpooling system

set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

# Load project env for DB credentials if available.
if [ -f ../.env ]; then
  set -a
  # shellcheck disable=SC1091
  source ../.env
  set +a
fi

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-${POSTGRES_USER:-carpool_user}}"
PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-change_me_postgres}}"
export PGHOST PGPORT PGUSER PGPASSWORD

# Host-run test processes should use host-reachable endpoints.
export TEST_DATABASE_URL="postgresql+psycopg2://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/carpooling_test"
export DATABASE_URL="${TEST_DATABASE_URL}"
export REDIS_URL="${TEST_REDIS_URL:-redis://127.0.0.1:6379/0}"
export KAFKA_BOOTSTRAP_SERVERS="${TEST_KAFKA_BOOTSTRAP_SERVERS:-127.0.0.1:9092}"

echo "🧪 Running Carpooling System Test Suite"
echo "========================================"
echo ""

# Create test database if it doesn't exist
echo "📊 Setting up test database..."
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" carpooling_test 2>/dev/null || echo "Test database already exists"

# Ensure schema always matches current models/init.sql
psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" carpooling_test -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" carpooling_test < database/init.sql

echo ""
echo "🧪 Running tests..."
echo ""

# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Test run complete!"
echo "📊 Coverage report generated in htmlcov/index.html"
