#!/usr/bin/env bash
# One-time install: run the meeting orchestrator every 5 minutes via LaunchAgent.
# No manual start — Gerald will poll Gmail and join meetings automatically.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$REPO_ROOT/launchd/com.openclaw.meeting-orchestrator.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.openclaw.meeting-orchestrator.plist"
mkdir -p "$REPO_ROOT/logs"
sed "s|{{REPO_ROOT}}|$REPO_ROOT|g" "$PLIST_SRC" > "$PLIST_DEST"
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "Installed. Meeting orchestrator runs every 5 min (and at login). Logs: $REPO_ROOT/logs/meeting_orchestrator_launchd.{log,err}"
echo "To stop: launchctl unload $PLIST_DEST"
