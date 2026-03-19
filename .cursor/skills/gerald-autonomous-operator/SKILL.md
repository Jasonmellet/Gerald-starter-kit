---
name: gerald-autonomous-operator
description: Run and troubleshoot Gerald autonomous prospecting and outreach workflows using the gerald CLI, including discover/analyze/score/draft/review/report stages. Use when the user asks to run Gerald pipelines, inspect outreach results, or debug why runs skipped contacts.
---

# Gerald Autonomous Operator

## Use when

- User asks to run Gerald pipeline or autonomous mode
- User asks why outreach did not send or skipped prospects
- User asks for run-level reports and summaries

## Required reads

- `gerald/README.md`
- `docs/GERALD-FOLLOW-UP-REPLIES.md`
- `docs/reference/x-automation-rules.md`

## Setup and run commands

From `gerald/`:

- `python -m app.cli.main init-db`
- `python -m app.cli.main discover`
- `python -m app.cli.main analyze`
- `python -m app.cli.main score`
- `python -m app.cli.main draft`
- `python -m app.cli.main run-pipeline`
- `python3 -m app.cli.main run-autonomous`

From repo root alternative:

- `./run run-autonomous`

## Troubleshooting flow

1. Confirm environment and send mode:
   - check `.env` values used by `app/config.py`
2. Check run outputs and reports:
   - outreach and run reports under `gerald/outputs/` when present
3. Explain skips by stage:
   - discovery filters
   - ICP thresholding
   - score thresholds
   - review/send mode guards
4. For follow-up reply failures, apply waterfall logic and policy constraints from:
   - `docs/GERALD-FOLLOW-UP-REPLIES.md`
   - `docs/reference/x-automation-rules.md`

## Output format

```markdown
# Gerald Pipeline Report

- Command: <run command>
- Result: <ok / partial / fail>
- Run summary: <counts for candidates, analyzed, scored, drafted, sent/skipped>

## Stage analysis
- Discovery: <key outcome>
- Analyze: <key outcome>
- Score: <key outcome>
- Draft/Send: <key outcome>

## Blocks and fixes
- <blocker + fix>

## Recommended next action
- <single next step>
```

## Guardrails

- Do not claim messages were sent unless logs/reports show send success.
- Treat X policy constraints as hard limits for automated replies.
