#!/usr/bin/env bash
set -euo pipefail
(cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e . && uvicorn app.main:app --reload --port 8000) &
BACK_PID=$!
(cd frontend && npm install && npm run dev) &
FRONT_PID=$!
trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' EXIT
wait
