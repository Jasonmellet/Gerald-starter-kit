# Recall.ai — 30 concurrent bot limit & why Gerald joined so many meetings

## What went wrong (root cause)

1. **Missing start_time → join anyway**  
   If an invite had no parseable start time (e.g. .ics not parsed, or wrong format), the code **defaulted to joining**. So every calendar email that looked like an invite but had no time caused a new bot.

2. **Wide time window**  
   We joined any meeting “in the next 30 minutes” or “started up to 15 minutes ago.” With many invites in the inbox (recurring, past meetings, etc.), that could create a bot for each one in that window.

3. **Orchestrator always creating bots**  
   There was no way to turn off joining; as long as the orchestrator was running, it kept creating bots for every matching invite.

## What we fixed (in code)

- **Orchestrator** now deletes each bot on Recall after the meeting is processed (or when a meeting is rescheduled). That stops new buildup.
- **Status detection** — Recall’s API doesn’t return a top-level `status`; we derive it from `status_changes` so “done” and “fatal” (and similar) are detected correctly for completion and cleanup.
- **No join when start_time is missing** — If we can’t parse the meeting time, we **do not** join (we used to join by default).
- **Pause switch** — Gerald joins by default when the orchestrator runs. Only set `RECALL_JOIN_ENABLED=false` in `.env` if you want to temporarily pause (e.g. vacation). No manual “turn on” needed for normal use.
- **Tighter window** — We only join if the meeting starts in the **next 15 minutes** (configurable via `RECALL_JOIN_WINDOW_MINUTES`) or started at most **5 minutes** ago (`RECALL_JOIN_GRACE_MINUTES`). Reduces accidental joins from old or recurring invites.
- **Re-check until join or ended** — We only mark an invite “processed” when we’ve joined, the meeting has already ended, or we already have a bot for that invite. So “starts in 2 hours” is re-checked every poll; when the start time enters the window we create a bot. Reschedules are handled the same way (new time re-checked until in window).

## You hit the limit — how to free slots

Recall’s API often **does not** allow deleting bots that have already joined or completed (you may get 405). So:

1. **Run the cleanup script** (it will try to delete and show the status breakdown):
   ```bash
   cd /Users/jcore/Desktop/Openclaw && python3 tools/recall_cleanup.py
   ```
2. **Use the Recall dashboard** to cancel or remove old/completed bots and free slots:
   - Go to [Recall dashboard](https://app.recall.ai/) (or your Recall project).
   - Find bots that are **done**, **failed**, or **media_expired** and cancel/delete them there.
3. After you’re under the limit, the orchestrator can create new bots again. Going forward, bots will be deleted automatically after each meeting.

## Upcoming meetings and reschedules

**Gerald joins your meetings automatically.** No config to flip.

1. **Run the orchestrator** (or run it on a schedule, e.g. cron every 5 min). It polls Gmail and creates a bot when each meeting’s start time enters the join window:
   ```bash
   cd /Users/jcore/Desktop/Openclaw && python3 tools/meeting_orchestrator.py
   ```
   Keep it running (or run it via cron every few minutes, e.g. every 5 min). It will:
   - Poll Gmail for calendar invites.
   - For each invite with a valid start time, re-check every poll until the meeting is “in window” (starts in the next 15 min or started up to 5 min ago), then create a bot. So you don’t have to start the orchestrator at an exact time — just have it running and it will join on time.

3. **Reschedules**  
   If a meeting is moved (new invite or updated .ics):
   - We detect the same meeting URL with a different invite (reschedule).
   - We drop the old bot and use the new start time.
   - If the new time is in the future, we don’t mark it “processed,” so we keep re-checking. When the new time enters the 15‑minute window we create a bot. So Gerald joins at the **new** time.

4. **Optional**  
   - `RECALL_JOIN_WINDOW_MINUTES=20` — create the bot up to 20 min before start (default 15).  
   - `RECALL_JOIN_GRACE_MINUTES=10` — still join if the meeting started up to 10 min ago (default 5).

---

## Summary

| Action | Who |
|--------|-----|
| Delete bots after each meeting | Orchestrator (automatic) |
| Free existing 30+ bots | You: Recall dashboard or `recall_cleanup.py` (leave_call for running bots) |
| Gerald joins meetings | Default: just run `meeting_orchestrator.py` (or cron it). No .env toggle. |
| Pause joining (e.g. vacation) | Set `RECALL_JOIN_ENABLED=false` in `.env` |
