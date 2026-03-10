---
name: meeting-transcription
description: Join and transcribe live meetings via Recall.ai; monitor Gmail for invites, run the orchestrator, and extract customer mentions. Use when the user asks about meeting transcription, Recall, joining calls, or setting up the meeting bot.
---

# Meeting Transcription Skill

Integrates Recall.ai with Gmail to automatically join meetings, transcribe them, and extract customer mentions.

## Overview

This skill allows Gerald to:
- Monitor `gerald@allgreatthings.io` for calendar invites
- Automatically join meetings via Recall.ai bot
- Transcribe the meeting
- Extract and classify customer mentions
- Save summaries to `memory/meetings/`
- **Email meeting summaries to jason@allgreatthings.io**

## Setup

1. **Credentials added** ✓
   - **Recall API key** in the **root `.env`** (this folder — same file as MOONSHOT etc.)
   - Gmail credentials in `credentials/gmail-credentials.json`

2. **Install dependencies:**
   ```bash
   pip install requests google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

3. **First-time OAuth:**
   - Run: `python3 tools/meeting_orchestrator.py`
   - Browser will open for Google authentication
   - Token saved to `credentials/gmail-token.pickle`

## Usage

### Automatic Mode
```bash
python3 tools/meeting_orchestrator.py
```
Runs continuously, polling Gmail every 60 seconds for new invites.

### Manual Mode (for testing)
```python
from tools.meeting_orchestrator import MeetingOrchestrator

orch = MeetingOrchestrator()
orch.run_once()  # Single poll cycle
```

### Manual Meeting Join
```python
from tools.recall_client import RecallAIClient

client = RecallAIClient()
bot = client.create_bot("https://zoom.us/j/123456", name="Gerald")
print(f"Bot ID: {bot['id']}")
```

### Send Meeting Summary via Email

Send meeting summaries to jason@allgreatthings.io:

```bash
# Send a specific meeting summary file
python3 tools/send_email.py --meeting 2026-03-06_Team_Meeting_summary.md

# Send with custom recipient
python3 tools/send_email.py --meeting summary.md --to other@example.com

# Send a custom email
python3 tools/send_email.py --subject "Hello" --body "Meeting notes attached" --to jason@allgreatthings.io
```

**First-time setup for sending:** You'll need to re-authenticate with Gmail to grant send permissions. Run any send command and a browser will open for OAuth consent.
```

## Output

Meetings are saved to `memory/meetings/`:
- `{date}_{subject}_analysis.json` - Full structured data
- `{date}_{subject}_summary.md` - Human-readable summary

## Security

- OAuth tokens stored in `credentials/` (gitignored)
- Gmail scopes: `gmail.readonly` (for invites) and `gmail.send` (for sending summaries)
- Meeting data stored locally only
- No cloud sync of transcripts

## File Structure

```
tools/
  recall_client.py          - Recall.ai API wrapper
  gmail_client.py           - Gmail OAuth + invite parsing + email sending
  meeting_processor.py      - Customer extraction + analysis
  meeting_orchestrator.py   - Main coordinator
  send_email.py             - Email sender CLI tool
```
