#!/bin/bash
# Test runner script for carpooling system

cd "$(dirname "$0")"
source .venv/bin/activate

echo "🧪 Running Carpooling System Test Suite"
echo "========================================"
echo ""

# Create test database if it doesn't exist
echo "📊 Setting up test database..."
createdb carpooling_test 2>/dev/null || echo "Test database already exists"
psql carpooling_test < database/init.sql 2>/dev/null || echo "Schema already initialized"

echo ""
echo "🧪 Running tests..."
echo ""

# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Test run complete!"
echo "📊 Coverage report generated in htmlcov/index.html"