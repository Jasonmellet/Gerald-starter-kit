#!/usr/bin/env bash
# Apply OpenClaw cron jobs (must run in Terminal.app — macOS blocks crontab from some IDE/automation contexts).
# Uses ~/Openclaw when your working copy lives under Desktop (same rule as turn_on_team.sh).
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CRON_ROOT="$REPO"
if [[ "$REPO" == *"Desktop"* ]]; then
  CRON_ROOT="$HOME/Openclaw"
  mkdir -p "$CRON_ROOT"
  echo "Syncing $REPO → $CRON_ROOT ..."
  rsync -a "$REPO/" "$CRON_ROOT/"
fi

strip_openclaw_cron() {
  # Match actual crontab lines: `python3 tools/scheduler.py` (no `/` before tools)
  crontab -l 2>/dev/null \
    | grep -v 'python3 tools/scheduler.py >> logs/scheduler.log' \
    | grep -v 'python3 tools/x_lead_feed.py >> logs/x_lead_feed.log' \
    | grep -v 'python3 tools/meeting_orchestrator_health_check.py >> logs/meeting_orchestrator_health.log' \
    | grep -v '^# OpenClaw Daily Schedule$' \
    | grep -v '^# OpenClaw meeting orchestrator watchdog$' \
    | grep -v '^# OpenClaw CSO / memory maintenance$' \
    | grep -v 'weekly_research.sh' \
    | grep -v 'daily_security.sh' \
    | grep -v 'daily_memory.sh' \
    || true
}

TMP="$(mktemp)"
strip_openclaw_cron > "$TMP"
{
  cat "$TMP"
  echo ""
  echo "# OpenClaw CSO / memory maintenance"
  echo "0 9 * * 1 cd $CRON_ROOT && /bin/bash tools/weekly_research.sh"
  echo "0 8 * * * cd $CRON_ROOT && /bin/bash tools/daily_security.sh"
  echo "59 23 * * * cd $CRON_ROOT && /bin/bash tools/daily_memory.sh"
  echo ""
  echo "# OpenClaw Daily Schedule"
  echo "30 8 * * * cd $CRON_ROOT && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1"
  echo "0 9 * * * cd $CRON_ROOT && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1"
  echo "0 18 * * * cd $CRON_ROOT && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1"
  echo "0 7 * * * cd $CRON_ROOT && /usr/bin/python3 tools/x_lead_feed.py >> logs/x_lead_feed.log 2>&1"
  echo "# OpenClaw meeting orchestrator watchdog"
  echo "*/15 * * * * cd $CRON_ROOT && /usr/bin/python3 tools/meeting_orchestrator_health_check.py >> logs/meeting_orchestrator_health.log 2>&1"
} > "${TMP}.new"
crontab "${TMP}.new"
rm -f "$TMP" "${TMP}.new"
echo "Done. OpenClaw cron now uses: $CRON_ROOT"
crontab -l | grep -E 'Openclaw|OpenClaw|scheduler|x_lead|meeting_orchestrator_health|weekly_research|daily_security|daily_memory' || true
