#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCHD_DIR"
mkdir -p "$REPO_ROOT/tools/x_system_logs"

# Ensure scripts are executable
chmod +x "$REPO_ROOT/tools/x_system_job.sh"
chmod +x "$REPO_ROOT/tools/x_system_monitor_window.sh"

install_plist() {
  local src="$1"
  local label="$2"
  local dest="$LAUNCHD_DIR/$label.plist"
  sed "s|{{REPO_ROOT}}|$REPO_ROOT|g" "$src" > "$dest"
  launchctl unload "$dest" 2>/dev/null || true
  launchctl load "$dest"
  echo "Loaded $label"
}

install_plist "$REPO_ROOT/launchd/com.openclaw.xsystem-research.plist" "com.openclaw.xsystem-research"
install_plist "$REPO_ROOT/launchd/com.openclaw.xsystem-draft.plist" "com.openclaw.xsystem-draft"
install_plist "$REPO_ROOT/launchd/com.openclaw.xsystem-publish.plist" "com.openclaw.xsystem-publish"
install_plist "$REPO_ROOT/launchd/com.openclaw.xsystem-monitor.plist" "com.openclaw.xsystem-monitor"

echo
echo "Installed X system launchd jobs:"
echo "  - research: daily 07:50"
echo "  - draft: daily 08:00 and 13:00"
echo "  - publish: daily 09:00 and 14:00"
echo "  - monitor: every 10 minutes (only runs 08:00-19:59 America/Chicago)"
echo
echo "Logs: $REPO_ROOT/tools/x_system_logs/"
echo "To stop all:"
echo "  launchctl unload \"$HOME/Library/LaunchAgents/com.openclaw.xsystem-research.plist\""
echo "  launchctl unload \"$HOME/Library/LaunchAgents/com.openclaw.xsystem-draft.plist\""
echo "  launchctl unload \"$HOME/Library/LaunchAgents/com.openclaw.xsystem-publish.plist\""
echo "  launchctl unload \"$HOME/Library/LaunchAgents/com.openclaw.xsystem-monitor.plist\""

