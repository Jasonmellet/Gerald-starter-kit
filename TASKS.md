# TASKS.md — Work queue and backlog

Gerald may append to Active when given a new task; move items to Completed when done; add to Ideas when the user suggests future work.

---

## Pending activation (run in Terminal)

**When Gerald creates a cron job, LaunchAgent, or script that needs to be run once to activate, he adds it here.** You run the command; then tell him it’s done so he can remove or check it off.

- _(None.)_

---

## Active Tasks

### Recurring / Ongoing

- **Weekly OpenClaw security review** — Check OpenClaw GitHub releases, security advisories, and changelog for updates. Analyze before upgrading. Added 2026-03-08.

### Waiting on Jason / External Action

- **X outreach: permissions + DM reality check** — Gerald has sent some DMs successfully; many failures are **403 “no permission to DM”** (recipient allows DMs only from followers / mutuals, or account settings). **Still verify** in X Developer Portal that app **Jmellet_AGT_Gerald_V2** has **Read + Write + DM** as intended, and OAuth **user-context** tokens in `.env` match that app. Prefer **public replies** or **follow-first** where cold DM is blocked. Playbook: `.cursor/skills/x-oauth-and-permissions-playbook/SKILL.md`. Added 2026-03-10; wording updated 2026-03-31 to match observed behavior.

## Completed Tasks

- **Cancel extra Cursor.ai account** — Sent reminder email to jenmellet@gmail.com on 2026-03-10. Completed 2026-03-10.
- **Build meeting transcription integration** — Gmail OAuth, Recall.ai client, meeting orchestrator, iCal parsing, transcript API, LaunchAgent/setup script, summary emails. Completed 2026-03-11.

---

## Ideas / Future Tasks

- **Review Matthew Berman's OpenClaw security framework** — He posted a 6-layer defense system (2,800 lines, 132 tests) for prompt injection protection. Analyze for nuggets we can implement. Tweet: https://x.com/matthewberman/status/2030423565355676100. Added 2026-03-09.
- _(Add ideas here, or ask your agent to analyze a YouTube video — see YOUTUBE-WORKFLOW.md.)_
