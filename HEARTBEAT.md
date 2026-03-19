# HEARTBEAT.md

Keep heartbeat work small and useful.

## Default behavior

- If nothing below needs attention, reply `HEARTBEAT_OK`.
- Do not revive stale tasks from old chats unless they are written in workspace files.
- Prefer one useful check over a long status dump.

## Recurring checks

- Review `TASKS.md` for active items that still need movement.
- If **Pending activation** in TASKS.md has items, remind the user once: "You have N command(s) in TASKS.md under Pending activation that need to be run in Terminal to activate what I set up."
- Check whether `LOGBOOK.md` should be updated for major completed work.
- If it has been more than 24 hours since the last maintenance pass, run a light daily review:
  read `AGENTS.md`, `MEMORY.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, and `HEARTBEAT.md`, then note contradictions, stale instructions, or missing memory updates.
- If the daily review finds something worth preserving, write it to the correct file instead of only mentioning it in chat.
- **X Monitor Check (Daily)** — Run `python3 tools/x_multi_monitor.py --once` once per day to check for new tweets from monitored accounts (matthewberman, neilpatel, dataforseo, steipete, gregisenberg). Alert if new tweets found. Cost: ~$0.11/day = ~$3.30/month.
- **Task Deadline Check** — Run `python3 tools/task_reminder.py --check` to check TASKS.md for deadlines. Execute actions (send emails, reminders) for due tasks.
- **Daily Digest Email (Daily 9am)** — Run `python3 tools/daily_digest.py` to send email summary of X monitor findings. Always sends at 9am, even if no new content. Data collection happens at 8:30am.
- **Security Review (Weekly Monday 9am)** — Run `python3 tools/security_review.py --email` to check OpenClaw updates and send security report.
- **CRO Skill Status (every 2 days)** — Read `skills/fractional-cro/TODO.md`; check Upwork and X/Twitter API status (saved credentials / ask Jason if account validated); if any API approved, test connection, update scraper, notify Jason, remove from pending; update TODO.md with last-checked date. If nothing new: "CRO Skill: No API approvals yet. Will check again in 2 days."

## Quiet rules

- Stay quiet late at night unless something is actually important.
- If there is no real update, respond only with `HEARTBEAT_OK`.
