---
name: team-activation-and-scheduler-doctor
description: Activate and diagnose Gerald team scheduling on macOS, including cron and launchd setup for scheduler, lead feed, and meeting orchestration. Use when the user says the team is idle, asks to turn everything on, or requests cron/launchd troubleshooting.
---

# Team Activation And Scheduler Doctor

## Use when

- User asks to "turn on the team"
- Automations are not running
- Cron or launchd setup/debug is requested

## Required reads

- `docs/WHY-THE-TEAM-IS-IDLE.md`
- `TASKS.md`
- `HEARTBEAT.md`

## Activation workflow

1. Prefer one-shot activation:
   - Run `./tools/turn_on_team.sh`
2. If user wants manual steps instead:
   - Run `bash tools/install_cron.sh`
   - Run `./tools/setup_gerald_meetings.sh`
3. Confirm schedule expectations:
   - `tools/scheduler.py` via cron at 8:30, 9:00, 18:00
   - `tools/x_lead_feed.py` daily
   - meeting orchestrator via LaunchAgent every 5 min

## Diagnosis workflow

1. Verify cron exists:
   - `crontab -l`
2. Verify launchd state and plist load:
   - `launchctl list | rg openclaw`
3. Check logs for failures:
   - `logs/scheduler.log`
   - `logs/x_lead_feed.log`
   - `logs/meeting_orchestrator_launchd.log`
   - `logs/meeting_orchestrator_launchd.err`
4. If repo is on Desktop and launchd fails with permission errors, re-run:
   - `./tools/setup_gerald_meetings.sh`

## Output format

```markdown
# Team Scheduler Status

- Activation state: <active / partial / inactive>
- Cron: <ok / missing / error>
- Meeting LaunchAgent: <ok / missing / error>
- Lead feed schedule: <ok / missing / error>

## Findings
- <root cause 1>
- <root cause 2>

## Actions taken
- <command and result>

## Next step
- <single recommended next action>
```

## Guardrails

- Never claim "active" unless activation command was actually run successfully.
- If activation cannot be executed in-session, provide exact commands for the user to run.
- Keep `TASKS.md` pending activation list consistent with what was run.
