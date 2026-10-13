#!/bin/bash
# Load .env, then run the sync. Log to logs/sync.log.
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

mkdir -p logs

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: .env not found in $PROJECT_DIR" >&2
  exit 1
fi

exec .venv/bin/python scripts/garmin/garmin_sync_coros.py
