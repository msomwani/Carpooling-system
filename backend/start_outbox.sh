#!/bin/bash
# This finds the directory where this script is located
cd "$(dirname "$0")"

# Activate virtual environment (adjust path if your venv is named differently)
source .venv/bin/activate

# Run the outbox processor
python -m app.workers.outbox_processor