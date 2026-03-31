# Gerald meetings: invite → he joins → transcribes → emails you

**One-time setup (macOS). Then you do nothing.**

From the repo (Terminal):

```bash
./tools/setup_gerald_meetings.sh
```

That script installs a LaunchAgent that runs every 5 minutes (and once at login). If the repo is on your Desktop, it copies the repo to `~/Openclaw` and installs from there so the agent can run (macOS blocks launchd from reading Desktop).

**After setup:**

1. **Invite** gerald@allgreatthings.io to a meeting (Google Calendar / Meet).
2. **Gerald joins** when the meeting is in the next 15 minutes or has just started (within 5 min).
3. **Recall** records and transcribes (built-in Recall.ai transcription).
4. **After the meeting** the orchestrator picks up the completed bot, gets the transcript, and **emails you the summary** (from gerald@allgreatthings.io).

No manual start, no running scripts. Just invite him.

## Logs

- `logs/meeting_orchestrator_launchd.log` — stdout
- `logs/meeting_orchestrator_launchd.err` — stderr

## Stop automatic runs

```bash
launchctl unload ~/Library/LaunchAgents/com.openclaw.meeting-orchestrator.plist
```

## Re-enable

```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.meeting-orchestrator.plist
```

## Python path

The plist uses `/usr/bin/python3`. If you use Homebrew Python, edit `launchd/com.openclaw.meeting-orchestrator.plist` and change the first `ProgramArguments` entry to e.g. `/opt/homebrew/bin/python3`, then re-run the install script.
