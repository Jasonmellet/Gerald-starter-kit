# X Local Automation System (Mac Mini)

This is a local, deterministic X automation engine with optional AI assistance.

## What it does

- Researches niche topics and tracked accounts.
- Scores posts by engagement + ICP relevance.
- Extracts practical patterns.
- Plans and generates candidate posts (template-first).
- Optionally improves copy with AI (best-effort only).
- Ranks and publishes one post.
- Monitors replies in one-pass checks (scheduler-driven every 10 min during active hours).
- Classifies replies and decides:
  - ignore
  - public reply only
  - public reply + DM
- Sends outbound DMs only when intent threshold is met.
- Logs all actions and writes local artifacts/state.

## Project layout

- `tools/x_system_run.py` — entrypoint
- `tools/x_system/` — modules
- `tools/x_system_config/` — config files
- `tools/x_system_data/` — run artifacts
- `tools/x_system_state/` — idempotency/recovery state
- `tools/x_system_logs/pipeline.log` — logs

## Dependencies

Install once:

```bash
python3 -m pip install -r tools/x_system/requirements.txt
```

## Environment variables

Required in `.env` (workspace root):

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`
- `X_BEARER_TOKEN`

Notes:

- Write actions (post/reply/dm-send) use OAuth 1.0a (proven path).
- DM read endpoints are intentionally not used.

Optional:

- `OPENAI_API_KEY` if you later enable `ai_enabled` in `tools/x_system_config/config.json`.

## Run commands

From repo root:

```bash
python3 tools/x_system_run.py research
python3 tools/x_system_run.py draft
python3 tools/x_system_run.py publish
python3 tools/x_system_run.py monitor
python3 tools/x_system_run.py full
python3 tools/x_system_run.py full --dry-run
```

## Dry-run behavior

Dry-run executes research/planning/classification logic and writes all artifacts/state,
but simulates:

- post publish
- public replies
- DMs

No X write calls are made in dry-run.

## Duplicate prevention + recoverability

- `tools/x_system_state/handled_replies.json` prevents duplicate reply handling.
- `tools/x_system_state/dm_sent.json` prevents duplicate DMs per `(campaign_id, user_id)`.
- `tools/x_system_state/posts.json` tracks published post metadata.
- `tools/x_system_state/pipeline_state.json` stores last stage + timestamps.

## Scheduling on Mac Mini (launchd)

This repo includes launchd jobs for a 2-post/day autonomous schedule:

- research: daily `07:50`
- draft: daily `08:00` and `13:00`
- publish: daily `09:00` and `14:00`
- monitor: every 10 minutes, but only executes between `08:00-19:59` America/Chicago

Install/activate:

```bash
bash tools/install_x_system_launchd.sh
```

Logs are written to:

- `tools/x_system_logs/research.log`, `research.err`
- `tools/x_system_logs/draft.log`, `draft.err`
- `tools/x_system_logs/publish.log`, `publish.err`
- `tools/x_system_logs/monitor.log`, `monitor.err`

To stop:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.openclaw.xsystem-research.plist"
launchctl unload "$HOME/Library/LaunchAgents/com.openclaw.xsystem-draft.plist"
launchctl unload "$HOME/Library/LaunchAgents/com.openclaw.xsystem-publish.plist"
launchctl unload "$HOME/Library/LaunchAgents/com.openclaw.xsystem-monitor.plist"
```

