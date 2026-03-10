# Gerald research sandbox – setup and security

Hardened OpenClaw configuration for a safe, experimental AI agent environment (agent name: **Gerald**). The machine is a dedicated Mac Mini with no personal data and no real accounts; access is remote-only via screen sharing.

---

## 1. Recommended OpenClaw configuration

Use the file **`openclaw-gerald-sandbox.json`** in this directory.

**To apply on the research Mac:**

```bash
# Backup current config
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak

# Copy sandbox config (edit paths if your user is not 'gerald')
cp /path/to/Openclaw/openclaw-gerald-sandbox.json ~/.openclaw/openclaw.json

# Restart the gateway
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

**If your Mac user is not `gerald`:**  
Edit `openclaw-gerald-sandbox.json` and replace `/Users/gerald/agent-lab` with your sandbox path (e.g. `$HOME/agent-lab` or `/Users/jcore/agent-lab`). Do the same for `logging.file`.

---

## 2. Folder setup commands

Run on the research Mac (use `/Users/gerald/agent-lab` if the Mac user is `gerald`, otherwise `$HOME/agent-lab`):

```bash
# Create sandbox and logs directory
SANDBOX="${HOME}/agent-lab"
# Or for user gerald: SANDBOX="/Users/gerald/agent-lab"
mkdir -p "$SANDBOX/logs"

# Create the four workspace files
echo '# Agent lab notes\n\nUse this file for experiment notes.' > "$SANDBOX/notes.md"
echo 'Ideas for future experiments (one per line or short block).' > "$SANDBOX/ideas.txt"
printf 'id,name,value\n1,alpha,10\n2,beta,20\n3,gamma,30\n' > "$SANDBOX/sample.csv"
echo '# Summary\n\n(This file is for the agent to write a short summary.)' > "$SANDBOX/summary.md"

# Ensure OpenClaw can write logs (if using $SANDBOX/logs in config)
touch "$SANDBOX/logs/openclaw.log"
```

**Optional – pull extra Ollama models (mistral, phi3):**

```bash
ollama pull mistral
ollama pull phi3
```

---

## 3. How this sandbox protects the system

| Protection | Implementation |
|------------|----------------|
| **No shell execution** | `tools.deny: ["exec", "bash", "process"]` – agent cannot run terminal commands. |
| **No elevated mode** | `tools.elevated.enabled: false` – no bypass of safety checks or host execution. |
| **Restricted workspace** | `agents.defaults.workspace: "/Users/gerald/agent-lab"` – file tools (read/write/edit) are limited to this directory. Agent cannot read or write outside it. |
| **No destructive file access** | Workspace is the only writable area. Agent cannot modify system files, other home dirs, SSH keys, or arbitrary hidden files; only paths under the workspace. |
| **Local models only** | Only the `ollama` provider is configured (llama3.2, mistral, phi3). No OpenAI, Anthropic, or other remote providers. |
| **No external integrations** | No email, calendar, Slack, GitHub, SSH, or cloud API keys are configured. Isolated experimentation only. |
| **Logging** | `logging.file` points to the sandbox `logs/` directory; `logging.level: "debug"` captures agent decisions, tool calls, errors, and file access. |
| **Safe automation** | File summarization, planning, and research are allowed via read/write/edit. Exec, file modifications outside workspace, and network tools are denied or out of scope. |

This setup allows useful research (file summarization, planning agents, multi-agent experiments) while preventing dangerous capabilities (shell, host access, broad file system or network access).

---

## 4. Security checklist

Before treating the environment as secure, confirm:

- [ ] **Config applied** – `~/.openclaw/openclaw.json` is the hardened config (or equivalent with correct paths).
- [ ] **Workspace path** – `agents.defaults.workspace` points only to the sandbox directory (e.g. `/Users/gerald/agent-lab` or `$HOME/agent-lab`).
- [ ] **Exec disabled** – `tools.deny` includes `"exec"` (and preferably `"bash"`, `"process"`).
- [ ] **Elevated off** – `tools.elevated.enabled` is `false`.
- [ ] **Ollama only** – `models.providers` contains only `ollama`; no remote API keys in config or env for OpenClaw.
- [ ] **No sensitive integrations** – No Slack, email, GitHub, SSH, or cloud services configured.
- [ ] **Logging** – `logging.file` is under the sandbox (e.g. `.../agent-lab/logs/openclaw.log`) and `logging.level` is `"debug"` (or at least `"info"`).
- [ ] **Gateway restarted** – After any config change, the OpenClaw gateway (LaunchAgent) was restarted.

---

## 5. Test prompt for Gerald

Use this in the OpenClaw Control UI (or whatever client you use) to verify file access and summarization inside the sandbox:

**Prompt:**

> Read the files inside /agent-lab and create a short summary in summary.md

Expected behavior: Gerald uses the `read` tool on files in the workspace (notes.md, ideas.txt, sample.csv, etc.) and the `write` tool to update `summary.md` with a short summary. No shell execution or access outside the workspace.

---

## Files in this repo

- **`openclaw-gerald-sandbox.json`** – Hardened OpenClaw config (apply to `~/.openclaw/openclaw.json` on the research Mac).
- **`agent-lab/`** – Template sandbox (notes.md, ideas.txt, sample.csv, summary.md, logs/). Copy or re-create under `/Users/gerald/agent-lab` (or your chosen path) on the Mac.
- **`GERALD-SANDBOX-SETUP.md`** – This file (setup, security description, checklist, test prompt).

Do not enable exec, elevated mode, or remote model providers in this sandbox. It is for research and experimentation only, not for autonomous or production use.
