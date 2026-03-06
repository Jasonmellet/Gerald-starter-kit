# HEARTBEAT.md

Keep heartbeat work small and useful.

## Default behavior

- If nothing below needs attention, reply `HEARTBEAT_OK`.
- Do not revive stale tasks from old chats unless they are written in workspace files.
- Prefer one useful check over a long status dump.

## Recurring checks

- Review `TASKS.md` for active items that still need movement.
- Check whether `LOGBOOK.md` should be updated for major completed work.
- If it has been more than 24 hours since the last maintenance pass, run a light daily review:
  read `AGENTS.md`, `MEMORY.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, and `HEARTBEAT.md`, then note contradictions, stale instructions, or missing memory updates.
- If the daily review finds something worth preserving, write it to the correct file instead of only mentioning it in chat.

## Quiet rules

- Stay quiet late at night unless something is actually important.
- If there is no real update, respond only with `HEARTBEAT_OK`.
