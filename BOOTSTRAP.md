# BOOTSTRAP.md - Initial Setup Guide

_First-time setup for Gerald and the OpenClaw workspace._

## Step 1: Identity & Personality ✓

**Status:** Already configured
- Name: Gerald
- Creature: AI research agent in a sandbox
- Vibe: Helpful, direct, task-oriented
- Emoji: 🦞

Files: `IDENTITY.md`, `SOUL.md`

---

## Step 2: User Profile

**Status:** Needs configuration

Update `USER.md` with:
- [ ] Your name: Jason
- [ ] What to call you: Jason
- [ ] Pronouns: (optional)
- [ ] Timezone: America/Chicago (detected)
- [ ] Notes: Work context, preferences, projects

---

## Step 3: Core Integrations

### 3.1 OpenAI Codex (ChatGPT OAuth) — default model
**Status:** ✓ Active (OpenClaw default)
- Auth: OAuth profile `openai-codex:default` in `~/.openclaw/` (not API-key billing for the main agent path)
- Default model: `openai-codex/gpt-5.4` in `~/.openclaw/openclaw.json`
- Moonshot/Kimi is **still configured** as a provider (API key in `.env`, catalog in config) if you switch models; it is not the default anymore.

### 3.2 Moonshot AI (Kimi) — optional provider
**Status:** ✓ Available, not default
- `MOONSHOT_API_KEY` in `.env` (gateway/LaunchAgent may need `launchctl setenv` if the key changes — see `KIMI-SETUP.md`)
- Models such as `moonshot/kimi-k2.5` remain in the provider list; use only when you explicitly choose them.

### 3.3 Meeting Transcription (Recall.ai + Gmail)
**Status:** ⚠️ Partial — needs Gmail API enabled

**Configured:**
- ✓ Recall API key in `.env`
- ✓ Gmail OAuth credentials in `credentials/gmail-credentials.json`
- ✓ OAuth token for read-only access
- ✓ Email sending tool created

**Needs Action:**
- [ ] Enable Gmail API in Google Cloud Console
  - URL: https://console.developers.google.com/apis/api/gmail.googleapis.com/overview?project=965808949044
  - Click **Enable**
  - Wait 2-3 minutes for propagation
- [ ] Test sending email
- [ ] (Optional) Enable Google Calendar API if you want calendar monitoring

### 3.4 YouTube Ingest
**Status:** ✓ Ready
- yt-dlp binary present
- Transcription workflow ready

---

## Step 4: Directory Structure

**Status:** ✓ Created

```
/Users/jcore/Desktop/Openclaw/
├── agent-lab/           # Optional sandbox folder (see agent-lab/README.md)
│   └── CRO-CHECKLIST.md # Pointer to HEARTBEAT CRO item
├── credentials/         # OAuth tokens & secrets (gitignored)
├── memory/              # Daily notes & meeting logs
│   ├── meetings/        # Meeting transcripts & summaries
│   └── YYYY-MM-DD.md    # Daily memory files
├── skills/              # Skill definitions
├── tools/               # Python scripts
├── sources/             # YouTube transcripts & raw data
├── outputs/             # Analysis outputs
├── SOUL.md, IDENTITY.md, USER.md, MEMORY.md, HEARTBEAT.md, AGENTS.md  # Personality & ops (at root)
└── .env                 # API keys
```

---

## Step 5: Test Everything

Run these to verify setup:

```bash
# Test Recall.ai connection
python3 -c "from tools.recall_client import RecallAIClient; print('Recall client OK')"

# Test Gmail read access
python3 tools/gmail_client.py

# Test email sending (after Gmail API enabled)
python3 tools/send_email.py --to jason@allgreatthings.io --subject "Test" --body "Hello!"

# Test YouTube ingest
python3 tools/youtube_ingest.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## Step 6: Self-Improvement Research (DataForSEO)

**Status:** ✓ Active
- Budget: $10/month with full audit logging
- Weekly cron job: Every Monday at 9 AM
- Research topics rotate: OpenClaw, AI agents, marketing automation, LLMs

**Commands:**
```bash
# Run research query
python3 tools/research_agent.py --query "OpenClaw new features"

# Check trends
python3 tools/research_agent.py --trends --keywords "AI agents,automation"

# View spending
python3 tools/research_agent.py --status

# View audit log
python3 tools/research_agent.py --audit
```

---

## Step 7: Conversation & Action Logging

**Status:** ✓ Active
- SQLite database: `memory/gerald_logs.db`
- Logs all conversations, tool calls, API calls, emails
- Exportable to JSON

**Commands:**
```bash
# View database stats
python3 tools/logger.py --stats

# Export all logs to JSON
python3 tools/logger.py --export
```

---

## Step 8: Start Meeting Orchestrator

Once Gmail API is enabled:

```bash
# Run continuously to auto-join meetings
python3 tools/meeting_orchestrator.py
```

Or set up as a background service / cron job.

---

## Step 9: Delete This File

Once everything is working, delete this BOOTSTRAP.md — you're all set up!

---

## Quick Reference

| Task | Command |
|------|---------|
| Send email | `python3 tools/send_email.py --to jason@allgreatthings.io --subject "X" --body "Y"` |
| Send meeting summary | `python3 tools/send_email.py --meeting 2026-03-06_Meeting_summary.md` |
| Check Gmail | `python3 tools/gmail_client.py` |
| Process YouTube | `python3 tools/youtube_ingest.py "<URL>"` |
| Start meeting bot | `python3 tools/meeting_orchestrator.py` |
| Research topic | `python3 tools/research_agent.py --query "X"` |
| Check research spending | `python3 tools/research_agent.py --status` |
| View logs | `python3 tools/logger.py --stats` |

---

_Good to go! 🦞_
