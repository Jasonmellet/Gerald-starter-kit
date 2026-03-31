#!/usr/bin/env bash
# One-time: turn on Gerald's team (cron for digest/security/CRO, meeting orchestrator).
# Run from repo root: ./tools/turn_on_team.sh
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
mkdir -p logs

# Cron must cd to a path launchd/macOS can read. Desktop copies break some jobs; mirror to ~/Openclaw.
CRON_ROOT="$REPO"
if [[ "$REPO" == *"Desktop"* ]]; then
  CRON_ROOT="$HOME/Openclaw"
  mkdir -p "$CRON_ROOT"
  echo "=== 0. Sync Desktop repo → $CRON_ROOT (cron + launchd runtime) ==="
  rsync -a "$REPO/" "$CRON_ROOT/"
  echo "Sync done."
  echo ""
fi

echo "=== 1. Cron (scheduler, digest, Mon X report, lead feed, meeting health) ==="
# Logic lives in apply_openclaw_cron.sh (run same script in Terminal.app if crontab hangs from an IDE).
bash "$REPO/tools/apply_openclaw_cron.sh"

echo ""
echo "=== 2. Meeting orchestrator (LaunchAgent; if repo on Desktop, copies to ~/Openclaw) ==="
"$REPO/tools/setup_gerald_meetings.sh"

echo ""
echo "=== 3. Gerald prospecting (run-autonomous Mon/Wed/Fri 09:15) ==="
bash "$REPO/tools/install_gerald_autonomous_launchd.sh"

echo ""
echo "Done. Team is scheduled:"
echo "  - 7:00 daily: CRO lead feed (memory/x_lead_feed.json)"
echo "  - 8:30 daily: X monitor + task reminders"
echo "  - 9:00 daily: Daily digest email"
echo "  - 9:00 Mon: Security review email"
echo "  - 18:00 daily: X monitor"
echo "  - Every 15 min: Meeting orchestrator health check (Telegram alert on repeated failures)"
echo "  - Every 5 min: Meeting orchestrator (Gerald joins when invited)"
echo "  - Mon/Wed/Fri 09:15: Gerald run-autonomous (discover→draft→send per .env; log: gerald/outputs/launchd-autonomous.log)"
echo ""
echo "Heartbeat (HEARTBEAT.md) runs only when something sends Gerald a heartbeat poll (e.g. OpenClaw schedule)."
