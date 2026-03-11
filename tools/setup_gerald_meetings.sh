#!/usr/bin/env bash
# One-time setup: Gerald joins meetings on time, transcribes (Recall), and emails you the summary.
# Run once from the repo. If the repo is on Desktop, we copy it to ~/Openclaw so the
# LaunchAgent can run (macOS blocks launchd from reading Desktop).
set -e
REPO_NOW="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$HOME/Openclaw"

if [[ "$REPO_NOW" == *"Desktop"* ]]; then
  echo "Repo is on Desktop; launchd cannot read it. Copying to $TARGET and installing from there..."
  mkdir -p "$(dirname "$TARGET")"
  rsync -a "$REPO_NOW/" "$TARGET/" 2>/dev/null || cp -R "$REPO_NOW" "$TARGET"
  REPO_ROOT="$TARGET"
  echo "Using $REPO_ROOT for the agent. You can open $TARGET in Cursor and use it from there."
else
  REPO_ROOT="$REPO_NOW"
fi

"$REPO_ROOT/tools/install_meeting_orchestrator_launchd.sh"
echo ""
echo "Done. Gerald will:"
echo "  - Poll every 5 min (and at login)"
echo "  - Join when you invite him (meeting in next 15 min or just started)"
echo "  - Transcribe via Recall and email you the summary after the meeting"
echo "No further action needed. Just invite gerald@allgreatthings.io to a meeting."
