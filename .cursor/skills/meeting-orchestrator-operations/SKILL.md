---
name: meeting-orchestrator-operations
description: Operate and troubleshoot Gerald's automated meeting join/transcription/email pipeline via LaunchAgent, Gmail, and Recall.ai. Use when meetings are not joined, summaries are not emailed, or the user asks to set up/fix meeting automation.
---

# Meeting Orchestrator Operations

## Use when

- User asks "is meeting join working?"
- Gerald did not join a scheduled meeting
- Transcript summary email was not sent
- User wants one-command setup for meeting automation

## Required reads

- `RECALL-AUTO-RUN.md`
- `docs/GERALD-MEETINGS-HOW-IT-WORKS.md`
- `tools/meeting_orchestrator.py`
- `tools/setup_gerald_meetings.sh`

## Setup / repair command

Preferred one-time command:

- `./tools/setup_gerald_meetings.sh`

Why:
- If repo is on Desktop, script copies to `~/Openclaw` so launchd can run.
- Installs or refreshes LaunchAgent plist.

## Health checks

1. LaunchAgent file:
   - `~/Library/LaunchAgents/com.openclaw.meeting-orchestrator.plist`
2. Active logs (runtime path):
   - `~/Openclaw/logs/meeting_orchestrator_launchd.log`
   - `~/Openclaw/logs/meeting_orchestrator_launchd.err`
   - `~/Openclaw/logs/orchestrator.log`
3. State file:
   - `~/Openclaw/memory/meeting-state.json`
4. Successful cycle signs:
   - Recall and Gmail init succeed
   - Poll loop continues every interval
   - Bot creation and transcript processing occur around meeting times

## Watchdog alerting

Periodic watchdog command:

- `python3 tools/meeting_orchestrator_health_check.py`

Behavior:
- Tracks consecutive unhealthy checks in `~/Openclaw/logs/meeting_orchestrator_health_state.json` (or repo `logs/` fallback)
- Sends Telegram alert when failures reach threshold (default 3 checks)
- Sends recovery alert when health returns

Cron schedule (recommended):
- `*/15 * * * * cd <repo> && /usr/bin/python3 tools/meeting_orchestrator_health_check.py >> logs/meeting_orchestrator_health.log 2>&1`

## Common failure patterns

- `Operation not permitted` with Desktop path:
  - Re-run `./tools/setup_gerald_meetings.sh` and use `~/Openclaw` runtime.
- Intermittent Gmail API backend errors on one message:
  - Ensure invite scan continues by skipping bad message IDs instead of failing full cycle.
  - Increase scan breadth if needed with `MEETING_INVITE_SCAN_LIMIT` (default 200).
- Summary email send failures:
  - Ensure Gmail auth includes send scope (`authenticate_with_send()` path).
- Recall bot create 429/402:
  - Handle as provider limits/quota issues; verify account status.
- Waiting-room bot hangs after meeting ends:
  - Orchestrator now runs stale-bot cleanup each poll.
  - It exits/removes stale `in_waiting_room`/`joining_call` bots (including duplicate waiting bots when a completed bot already exists for that meeting).

## Output format

```markdown
# Meeting Automation Status

- Runtime path: <path>
- LaunchAgent: <ok / missing / misconfigured>
- Polling loop: <ok / fail>
- Join pipeline: <ok / partial / fail>
- Summary email path: <ok / fail>

## Evidence
- <key log lines and state>

## Actions taken
- <commands run>

## Next step
- <single recommended action>
```
