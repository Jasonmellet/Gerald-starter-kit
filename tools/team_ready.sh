#!/usr/bin/env bash
# One command: sync Desktop→~/Openclaw if needed, refresh cron paths, meeting + Gerald launchd.
set -e
exec "$(cd "$(dirname "$0")" && pwd)/turn_on_team.sh"
