#!/usr/bin/env bash
# Install LaunchAgent: Gerald run-autonomous Mon/Wed/Fri 09:15 (local time).
# Uses same Desktop → ~/Openclaw copy pattern as meeting orchestrator when needed.
set -e
REPO_NOW="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$HOME/Openclaw"

if [[ "$REPO_NOW" == *"Desktop"* ]]; then
  echo "Repo path is under Desktop; launchd may not execute reliably. Syncing to $TARGET ..."
  mkdir -p "$(dirname "$TARGET")"
  rsync -a "$REPO_NOW/" "$TARGET/" 2>/dev/null || cp -R "$REPO_NOW" "$TARGET"
  REPO_ROOT="$TARGET"
else
  REPO_ROOT="$REPO_NOW"
fi

GERALD="$REPO_ROOT/gerald"
SCRIPT="$GERALD/scripts/run-autonomous-daily.sh"
OUT_LOG="$GERALD/outputs/launchd-autonomous.log"
PLIST_SRC="$REPO_ROOT/launchd/com.gerald.run-autonomous.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.gerald.run-autonomous.plist"

if [[ ! -x "$SCRIPT" ]] && [[ -f "$SCRIPT" ]]; then
  chmod +x "$SCRIPT"
fi

mkdir -p "$GERALD/outputs"
chmod +x "$SCRIPT" 2>/dev/null || true

sed -e "s|REPO_ROOT_PLACEHOLDER|$REPO_ROOT|g" "$PLIST_SRC" > "$PLIST_DST"

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Installed: $PLIST_DST"
echo "Runs: Mon/Wed/Fri 09:15 — $SCRIPT"
echo "Logs: $OUT_LOG"
