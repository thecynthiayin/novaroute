#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
[[ -f .env ]] || cp .env.example .env
if [[ "${SKIP_SERVICES:-0}" != 1 ]]; then docker compose up -d --wait; fi
"$PYTHON_BIN" -c "import sys; assert sys.version_info[:2] == (3,12), 'Use Python 3.12 for the pinned stack'"
[[ -d backend/.venv ]] || "$PYTHON_BIN" -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-lock.txt
(cd backend && .venv/bin/python -m alembic upgrade head)
if [[ "${DEMO:-0}" == 1 ]]; then backend/.venv/bin/python database/seed.py --demo --limit 25 --seed 42; fi
[[ -f frontend/.env.local ]] || cp frontend/.env.example frontend/.env.local
(cd frontend && npm ci)
echo 'Setup complete. See README for native start commands and optional model warmup.'
