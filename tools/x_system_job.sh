#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-}"
if [[ -z "$MODE" ]]; then
  echo "Usage: $0 <research|draft|publish|monitor|full> [extra args]"
  exit 1
fi
shift || true

cd "$REPO_ROOT"
/usr/bin/python3 tools/x_system_run.py "$MODE" "$@"

