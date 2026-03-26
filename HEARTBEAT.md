# HEARTBEAT.md

Keep heartbeat work small and useful.

## Default behavior

- If nothing below needs attention, reply `HEARTBEAT_OK`.
- Do not revive stale tasks from old chats unless they are written in workspace files.
- Prefer one useful check over a long status dump.

## Recurring checks

- **TASKS review loop** — Read `TASKS.md` and classify active items as actionable now, blocked, or stale. If **Pending activation** has items, remind the user once: "You have N command(s) in TASKS.md under Pending activation that need to be run in Terminal to activate what I set up." If an item clearly needs movement or cleanup, either update `TASKS.md` or tell Jason what needs attention. Do not just notice drift; close the loop.
- **LOGBOOK verification loop** — Check whether major completed work is missing from `LOGBOOK.md`. If a meaningful action was completed and not logged, append the row, verify it exists, and only mention it if something was actually missing.
- **Daily maintenance loop (every 24h+)** — If it has been more than 24 hours since the last maintenance pass, read `AGENTS.md`, `MEMORY.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, and `HEARTBEAT.md`; look for contradictions, stale instructions, or missing memory updates; write important fixes to the correct file immediately; then log the maintenance pass.
- **X Monitor Check (Daily)** — Run `python3 tools/x_multi_monitor.py --once` once per day to check monitored accounts (matthewberman, neilpatel, dataforseo, steipete, gregisenberg). Alert only on signal worth surfacing, not just volume. If something should change tasks, memory, or priorities, say so. Cost: ~$0.11/day = ~$3.30/month.
- **Task Deadline Check** — Run `python3 tools/task_reminder.py --check`. If due actions exist, execute the needed reminders/actions, verify they ran, and update related files if the task state changed.
- **Daily Digest Email (Daily 9am)** — Run `python3 tools/daily_digest.py` to send the email summary of X monitor findings. Verify success or report failure; do not assume a send worked just because the command ran. Data collection happens at 8:30am.
- **Security Review (Weekly Monday 9am)** — Run `python3 tools/security_review.py --email`, inspect whether it found anything noteworthy, verify the email/report step succeeded, and surface important findings.
- **CRO Skill Status (every 2 days)** — Read `skills/fractional-cro/TODO.md`; check Upwork and X/Twitter API status (saved credentials / ask Jason if account validated). If any API is approved, test connection, update scraper, notify Jason, remove it from pending, and update TODO state. If nothing is approved, still update the last-checked date/state so the loop stays current. If nothing new: "CRO Skill: No API approvals yet. Will check again in 2 days."

## Quiet rules

- Stay quiet late at night unless something is actually important.
- If there is no real update, respond only with `HEARTBEAT_OK`.
