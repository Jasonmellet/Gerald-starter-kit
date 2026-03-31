#!/usr/bin/env bash
set -euo pipefail

# Run monitor only during 8:00-19:59 America/Chicago
CURRENT_HOUR="$(TZ=America/Chicago date +%H)"

if (( 10#$CURRENT_HOUR < 8 || 10#$CURRENT_HOUR >= 20 )); then
  echo "Skipping monitor outside 8am-8pm CDT window."
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/tools"
cd "$REPO_ROOT"
/usr/bin/python3 tools/x_system_run.py monitor

