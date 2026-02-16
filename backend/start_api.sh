#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python -m uvicorn app.main:app --reload