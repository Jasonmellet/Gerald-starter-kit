#!/usr/bin/env bash
# One-time: turn on Gerald's team (cron for digest/security/CRO, meeting orchestrator).
# Run from repo root: ./tools/turn_on_team.sh
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
mkdir -p logs

echo "=== 1. Installing cron (scheduler: 8:30, 9am, 6pm; Monday 9am security) ==="
crontab -l > /tmp/oc_crontab 2>/dev/null || true
if ! grep -q "OpenClaw Daily" /tmp/oc_crontab 2>/dev/null; then
  cat >> /tmp/oc_crontab << EOF

# OpenClaw Daily Schedule
30 8 * * * cd $REPO && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
0 9 * * * cd $REPO && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
0 18 * * * cd $REPO && /usr/bin/python3 tools/scheduler.py >> logs/scheduler.log 2>&1
EOF
  crontab /tmp/oc_crontab
  echo "Cron installed."
else
  echo "Cron already has OpenClaw entries."
fi

echo ""
echo "=== 2. Adding CRO lead feed (daily 7am) ==="
if ! crontab -l 2>/dev/null | grep -q "x_lead_feed.py"; then
  (crontab -l 2>/dev/null; echo "0 7 * * * cd $REPO && /usr/bin/python3 tools/x_lead_feed.py >> logs/x_lead_feed.log 2>&1") | crontab -
  echo "Lead feed cron added."
else
  echo "Lead feed already in crontab."
fi

echo ""
echo "=== 3. Adding meeting orchestrator health check (every 15 min) ==="
if ! crontab -l 2>/dev/null | grep -q "meeting_orchestrator_health_check.py"; then
  (crontab -l 2>/dev/null; echo "*/15 * * * * cd $REPO && /usr/bin/python3 tools/meeting_orchestrator_health_check.py >> logs/meeting_orchestrator_health.log 2>&1") | crontab -
  echo "Meeting health-check cron added."
else
  echo "Meeting health-check already in crontab."
fi

echo ""
echo "=== 4. Meeting orchestrator (LaunchAgent; if repo on Desktop, copies to ~/Openclaw) ==="
"$REPO/tools/setup_gerald_meetings.sh"

echo ""
echo "Done. Team is scheduled:"
echo "  - 7:00 daily: CRO lead feed (memory/x_lead_feed.json)"
echo "  - 8:30 daily: X monitor + task reminders"
echo "  - 9:00 daily: Daily digest email"
echo "  - 9:00 Mon: Security review email"
echo "  - 18:00 daily: X monitor"
echo "  - Every 15 min: Meeting orchestrator health check (Telegram alert on repeated failures)"
echo "  - Every 5 min: Meeting orchestrator (Gerald joins when invited)"
echo ""
echo "Heartbeat (HEARTBEAT.md) runs only when something sends Gerald a heartbeat poll (e.g. OpenClaw/Kimi schedule)."
