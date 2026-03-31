#!/usr/bin/env bash
# Run Gerald's full pipeline once (discover -> analyze -> score -> draft -> select top 5 -> send).
# Schedule this with cron or launchd to run Gerald automatically without opening a terminal.
#
# Example cron (run daily at 9:00 AM):
#   0 9 * * * /Users/jcore/Desktop/Openclaw/gerald/scripts/run-autonomous-daily.sh >> /Users/jcore/Desktop/Openclaw/gerald/outputs/cron.log 2>&1

set -e
GERALD_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$GERALD_DIR"
export PYTHONPATH="$GERALD_DIR"
python3 -m app.cli.main run-autonomous
