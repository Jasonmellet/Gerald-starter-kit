---
name: x-system-pipeline-operator
description: Operate and troubleshoot the local X automation pipeline across research, draft, publish, and monitor stages with dry-run safety and state/log inspection. Use when the user asks to run X pipeline stages, debug skipped posts, or inspect X system behavior.
---

# X System Pipeline Operator

## Use when

- User asks to run the X system
- Publish or monitor stage failed
- User requests dry-run checks before live posting

## Required reads

- `tools/X-SYSTEM-README.md`
- `docs/x-content-brief.md`
- `docs/x-icp-definition.md`
- `docs/reference/x-automation-rules.md`

## Standard commands

Run from repo root:

- `python3 tools/x_system_run.py research`
- `python3 tools/x_system_run.py draft`
- `python3 tools/x_system_run.py publish`
- `python3 tools/x_system_run.py monitor`
- `python3 tools/x_system_run.py full`
- `python3 tools/x_system_run.py full --dry-run`

## Triage checklist

1. Confirm env and config assumptions:
   - `.env` X credentials present
   - `tools/x_system_config/config.json` is valid
2. Check latest pipeline state:
   - `tools/x_system_state/pipeline_state.json`
3. Inspect logs:
   - `tools/x_system_logs/pipeline.log`
   - stage-specific `*.log` and `*.err` files
4. Inspect artifacts to explain behavior:
   - `tools/x_system_data/research/`
   - `tools/x_system_data/posts/`
   - `tools/x_system_data/replies/`
5. If launchd scheduling is expected, verify install script:
   - `bash tools/install_x_system_launchd.sh`

## Known failure patterns

- Desktop path + launchd: "Operation not permitted" -> re-run install script so jobs use `~/Openclaw`.
- 402/403 on search or publish -> billing/product tier limits in X portal, not code bug.
- No publish candidate -> ranking/constraints filtered everything; inspect generated candidates and hard constraints.

## Output format

```markdown
# X System Run Report

- Mode: <live / dry-run>
- Stage requested: <stage>
- Result: <ok / partial / fail>

## Evidence
- State file: <key values>
- Logs: <key lines summarized>
- Artifacts checked: <paths>

## Why this happened
- <root cause>

## Recommended next action
- <single next step>
```
