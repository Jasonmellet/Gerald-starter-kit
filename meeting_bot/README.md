# Meeting Bot

Standalone Python app: watch Gmail for calendar invites, join meetings via Recall.ai, transcribe, and email a summary. No other frameworks or agents.

## Setup

1. **Create venv and install deps**
   ```bash
   cd meeting_bot
   python3 -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Recall.ai**
   - Get an API key from [Recall.ai](https://recall.ai).
   - In `meeting_bot/.env` set `RECALL_API_KEY=...`.

3. **Gmail**
   - Put `gmail-credentials.json` (OAuth client credentials from Google Cloud Console) in `meeting_bot/credentials/`, **or** reuse the repo’s credentials by adding to your `.env` (repo root or `meeting_bot/.env`):
     ```
     GMAIL_CREDENTIALS_PATH=../credentials/gmail-credentials.json
     GMAIL_TOKEN_PATH=../credentials/gmail-token.pickle
     ```
   - Run once to complete OAuth and save the token:
     ```bash
     python -m meeting_bot.run --auth-only
     ```
   - Use a Gmail account that will receive calendar invites and that you want to use to send summary emails.

4. **Optional in `.env`**
   - `SUMMARY_EMAIL_TO` — where to send the summary (default: same as Gmail account).
   - `JOIN_WINDOW_MINUTES`, `JOIN_GRACE_MINUTES`, `JOIN_ENABLED`, `BOT_NAME` — see `.env.example`.

## Run

- **One poll then exit** (for cron or LaunchAgent):
  ```bash
  python -m meeting_bot.run --once
  ```
- **Re-check all invites once** (e.g. after fixing config):
  ```bash
  python -m meeting_bot.run --once --recheck
  ```
- **Loop every 5 minutes** (interactive):
  ```bash
  python -m meeting_bot.run --loop
  ```

State is in `meeting_bot/state/`. Output (JSON + markdown summaries) is in `meeting_bot/output/`.

## Schedule (e.g. every 5 min)

From the **meeting_bot** directory (or use absolute path):

```bash
# LaunchAgent (macOS): run install script that points at meeting_bot and uses:
#   ProgramArguments: /usr/bin/python3, /path/to/meeting_bot/run.py, --once
#   StartInterval: 300
```

Or cron:

```cron
*/5 * * * * cd /path/to/meeting_bot && .venv/bin/python -m meeting_bot.run --once >> logs/meeting_bot.log 2>&1
```

## What it does

1. Polls Gmail for calendar invites (`.ics` or invite subject).
2. For each invite whose start time is within the join window, creates a Recall.ai bot with **transcription enabled** (`recallai_streaming`, `prioritize_accuracy`).
3. When a bot finishes, fetches the transcript, runs the processor (customers, action items, topics), saves JSON + markdown under `output/`, and sends one summary email to `SUMMARY_EMAIL_TO`.
4. Keeps state so it doesn’t re-join the same meeting or re-process the same invite.

All logic is in this package; no external agent or OpenClaw dependency.
