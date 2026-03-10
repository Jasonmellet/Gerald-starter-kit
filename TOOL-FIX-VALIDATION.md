# Tool-calling fix — user steps and validation

Config has been updated per the diagnosis plan: debug logging enabled, primary model set to **qwen3-coder:30b**, Llama 3.1 8B kept as an option. Guardrails unchanged (exec/bash/process denied; local Ollama only).

**Note:** Ollama does not have a `qwen3-coder:14b` tag. The smallest Qwen3 Coder in the library is **qwen3-coder:30b** (about 19GB). If you have 16GB RAM, it may use swap; if you hit out-of-memory errors, try **glm-4.7-flash** instead (`ollama pull glm-4.7-flash` and set primary to `ollama/glm-4.7-flash` in config).

## 1. Pull the new model (required)

In Terminal:

```bash
ollama pull qwen3-coder:30b
```

Wait until the download finishes. Until this is done, OpenClaw may fail or fall back when using the new primary model.

## 2. Gateway restart (already done)

The OpenClaw gateway was restarted after the config change. If you change config again later:

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

## 3. Validation

1. **New chat** in the OpenClaw Control UI (so the session uses the new primary model).
2. Send: *"Read notes.md, ideas.txt, and sample.csv and write a short summary to summary.md."*
3. **Check 1:** In the UI or session, the assistant should show **tool use** (read/write) and then a short reply. No “roleplay” summary only in chat.
4. **Check 2:** Open `agent-lab/summary.md` — it should contain a real summary, not the original placeholder.
5. **Debug log (optional):** Logs are at `/tmp/openclaw/openclaw-YYYY-MM-DD.log` (or path in `logging.file` if set). At `logging.level: "debug"` you should see request/response detail, including whether tool definitions are sent and whether the model returns tool_calls.

If tool calls still do not appear or `summary.md` is unchanged, capture the latest session JSONL (under `~/.openclaw/agents/main/sessions/`) and the relevant debug log lines for further diagnosis.

## 4. Switching back to Llama 3.1 8B

Llama 3.1 8B remains in the model list. To use it again for chat-only (no reliance on tool use):

- In OpenClaw config, set `agents.defaults.model.primary` to `"ollama/llama3.1:8b"`, or
- Change the model in the UI if your client supports it.

Do not rely on Llama 3.1 8B for read/write tool tasks until tool_calls are confirmed for that model.
