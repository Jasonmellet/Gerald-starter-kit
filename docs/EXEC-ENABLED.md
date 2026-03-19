# Giving Gerald the ability to run commands (exec)

When exec is enabled, Gerald can run scripts and activation commands himself (cron, LaunchAgent, `tools/*.py`, `tools/*.sh`) instead of only creating files and asking you to run them.

## In Cursor

If you're chatting with Gerald in Cursor, the agent often has terminal/run access already. The workspace rules in **BOUNDARIES.md** and **AGENTS.md** tell him how to use exec safely (only workspace scripts and activation commands; no destructive or remote-pipe commands).

## OpenClaw gateway (Kimi, Discord, etc.)

If Gerald runs via the OpenClaw gateway, exec is controlled by the OpenClaw config.

**To enable exec:**

1. Back up your current config:
   ```bash
   cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
   ```

2. Use a config that allows exec. Either:
   - **Replace** with the workspace copy:  
     `cp /path/to/Openclaw/openclaw-gerald-with-exec.json ~/.openclaw/openclaw.json`  
     (Edit the file first if your workspace path or user is different: `agents.defaults.workspace`, `logging.file`.)
   - **Or edit** your existing `~/.openclaw/openclaw.json`: under `tools`, set `"allow": ["read", "write", "edit", "exec"]` and `"deny": []` (or remove `"exec"` from `deny`).

3. Restart the gateway:
   ```bash
   launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   ```

After that, Gerald can run activation commands (e.g. `./tools/turn_on_team.sh`, `bash tools/install_cron.sh`) and scripts under the workspace. **BOUNDARIES.md** limits exec to workspace scripts and activation commands; he must not run destructive commands or `curl ... | bash` from the internet.
