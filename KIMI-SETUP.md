# Kimi (Moonshot) setup

## 1. Add your API key

Edit `.env` in this folder and replace `your-kimi-api-key-here` with your real Kimi API key (from https://platform.moonshot.ai/). No quotes needed:

```
MOONSHOT_API_KEY=sk-your-actual-key
```

Save the file. `.env` is in `.gitignore` so the key is not committed.

## 2. Make the key available to OpenClaw

The OpenClaw gateway reads `MOONSHOT_API_KEY` from the environment. Choose one:

**Option A – Gateway run from terminal**  
If you start the gateway yourself:

```bash
cd /Users/jcore/Desktop/Openclaw
source .env
openclaw gateway --port 18789
```

**Option B – Gateway run by LaunchAgent (default)**  
So the background service sees the key, set it once in launchd then restart:

```bash
cd /Users/jcore/Desktop/Openclaw
export $(grep -v '^#' .env | xargs)
launchctl setenv MOONSHOT_API_KEY "$MOONSHOT_API_KEY"
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

(After reboot you may need to run the `launchctl setenv` line again, or add it to your shell profile and run it before loading the agent.)

## 3. Use Kimi in OpenClaw

- **Models available:** `moonshot/kimi-k2.5`, `moonshot/kimi-k2-turbo-preview`, `moonshot/kimi-k2-thinking`
- **Set as default:** In OpenClaw config set `agents.defaults.model.primary` to `"moonshot/kimi-k2.5"`, or pick the model in the Control UI.
- **Keep Ollama as default:** Leave primary as `ollama/qwen3-coder:30b` (or your current model) and choose Kimi only when you want it.

Restart the gateway after any config change.
