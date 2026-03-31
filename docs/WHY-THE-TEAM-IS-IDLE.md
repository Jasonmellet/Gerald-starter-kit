# Why the team isn’t doing anything

Short answer: **no schedule is active.** The skills (CRO, COO, CSO) and automations (meetings, digest, security review) only run when something triggers them. Right now nothing is.

---

## What we found

| Thing | Expected trigger | Actual state |
|-------|------------------|---------------|
| **Cron** | You run `tools/install_cron.sh` once; cron runs scheduler.py at 8:30, 9:00, 18:00 and (Mon 9am) security_review | **No crontab** → scheduler never runs |
| **Meeting orchestrator** | LaunchAgent runs `meeting_orchestrator.py --once` every 5 min | Plist exists but runs from Desktop → **Operation not permitted** (launchd can’t read Desktop) → no polls |
| **CRO (leads)** | Cron or you run `python3 tools/x_lead_feed.py` → writes `memory/x_lead_feed.json`; Gerald reads it when you ask for leads | No cron for lead feed; file only updates if you run the script |
| **COO** | You ask Gerald for business/ops/pricing help → he uses the skill | Reactive only; no automation |
| **CSO (Chief)** | Cron runs `weekly_research.sh` or security scripts | No cron for security → Chief never runs on a schedule |
| **Heartbeat** (X monitor, task reminders, daily digest, security review in HEARTBEAT.md) | Some “heartbeat poll” sends Gerald a message; he reads HEARTBEAT.md and runs the checklist | Only runs if OpenClaw/Kimi (or something) is configured to send heartbeat polls on a schedule; otherwise never |

So: **cron was never installed**, the **meeting LaunchAgent can’t run from Desktop**, and **heartbeat** only runs if something is pinging Gerald on a schedule.

---

## What to do (one-time)

1. **Turn on cron** (scheduler + lead feed + security):
   ```bash
   bash tools/install_cron.sh
   ```
   That installs the existing crontab that runs `scheduler.py` at 8:30, 9:00, 6:00 and (Monday 9am) security review.  
   Then add a line so the **CRO lead feed** runs daily, e.g.:
   ```bash
   crontab -e
   # Add:
   0 7 * * * cd /Users/jcore/Desktop/Openclaw && /usr/bin/python3 tools/x_lead_feed.py >> logs/x_lead_feed.log 2>&1
   ```

2. **Fix meeting orchestrator** (so Gerald can join meetings):
   ```bash
   ./tools/setup_gerald_meetings.sh
   ```
   If the repo is on Desktop, that script copies it to `~/Openclaw` and installs the LaunchAgent from there so launchd can run it.

3. **Heartbeat** (X monitor, task reminders, digest, security in HEARTBEAT.md):  
   Those run only when Gerald receives a heartbeat poll. If you use OpenClaw or Kimi with a scheduled “heartbeat” message, that’s what triggers them. If you never set that up, no one is triggering heartbeat, so those checks don’t run unless you ask Gerald to “do your heartbeat” in chat.

---

## One script to “turn on the team”

You can add a single script that (1) installs cron, (2) runs setup_gerald_meetings.sh so the meeting agent runs from a valid path, and (3) optionally adds the CRO lead-feed cron line. Then you run that script once and the team has a schedule.
