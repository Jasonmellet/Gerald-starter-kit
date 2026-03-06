# Gerald Starter Kit

A ready-to-use OpenClaw agent workspace. Clone it, add your API keys, point OpenClaw at this folder, and you get an agent that can read/write files, run scripts, analyze YouTube videos (captions), and follow a daily review and security checklist. You can rename the agent and make it yours.

**Repo:** [github.com/Jasonmellet/Gerald-starter-kit](https://github.com/Jasonmellet/Gerald-starter-kit)

---

## Get the kit

**Clone with git:**
```bash
git clone https://github.com/Jasonmellet/Gerald-starter-kit.git
cd Gerald-starter-kit
```

**Or** download **[v1.0 – Gerald Starter Kit](https://github.com/Jasonmellet/Gerald-starter-kit/releases)** as a zip and unpack it. Put the folder somewhere permanent (e.g. `~/Gerald` or `~/Openclaw/agent-lab`).

---

## What you need first

- **OpenClaw** installed and running (gateway + web UI or another channel).
- **Python 3** (for the YouTube ingest script).
- **yt-dlp** optional: a macOS binary is included in `tools/`; otherwise install with `brew install yt-dlp` or `pip3 install yt-dlp`.

---

## Quick setup

1. **Get the kit**  
   Use the clone or download steps above if you haven’t already.

2. **Secrets**  
   - Copy `.env.example` to `.env` **outside** this folder (in your OpenClaw config directory, e.g. the parent of this workspace or `~/.openclaw`).  
   - Paste your API key(s). For example, add a Kimi (Moonshot) key if you use that provider.  
   - Never commit `.env` or push it to GitHub.

3. **Point OpenClaw at this workspace**  
   Set the default agent workspace to this folder, e.g.:
   ```bash
   openclaw config set agents.defaults.workspace /path/to/this/folder
   ```
   Use the full path to the folder that contains `AGENTS.md`, `SOUL.md`, etc.

4. **Name your agent (optional)**  
   Open `IDENTITY.md` and change the name, vibe, and emoji. The default is "Gerald" — replace with whatever you like.

5. **First run**  
   Start a new OpenClaw session. The agent will run its startup sequence (read SOUL, boundaries, workflow, etc.) and greet you. If `BOOTSTRAP.md` is present, it will follow that once; you can delete it after onboarding.

---

## What’s in the kit

- **AGENTS.md** — How the agent operates, daily maintenance, model-routing guidance.
- **SOUL.md** — Persona and boundaries.
- **WORKFLOW.md** — Core loop and YouTube analysis steps.
- **YOUTUBE-WORKFLOW.md** — Full flow: ingest → read transcript → write analysis.
- **HEARTBEAT.md** — Lightweight recurring checks (tasks, logbook, daily review).
- **SECURITY-CHECKLIST.md** — Practices for secrets, dirty data, and audits.
- **TOOLS.md / TOOL-USE.md / BOUNDARIES.md** — Tool discipline and safety.
- **templates/** — e.g. YouTube analysis output template.
- **tools/** — e.g. `youtube_ingest.py` (and a macOS yt-dlp binary if included).
- **skills/** — e.g. YouTube ingest skill.

The agent has **read**, **write**, **edit**, and **exec**. It can run the YouTube ingest script itself, then read transcripts and write analyses to `outputs/`.

---

## YouTube analysis (captions-only)

1. In OpenClaw, ask the agent to analyze a video and paste the YouTube URL.
2. The agent will run `python3 tools/youtube_ingest.py "<URL>"`, read the transcript and metadata from `sources/`, and write an analysis to `outputs/` using the template.
3. Works only when the video has captions or subtitles; no audio transcription in this setup.

If exec isn’t available in your environment, you can run the ingest yourself in a terminal from this folder, then ask the agent to analyze (it will read from `sources/` and write to `outputs/`).

---

## What not to commit

- `.env` (API keys)
- `memory/` (daily and long-term agent memory)
- `outputs/` (generated analyses)
- `sources/` (downloaded transcripts/metadata)

These are in `.gitignore`. Keep them local so the repo stays a reusable starter kit.

---

## Making it yours

- Edit **IDENTITY.md** — name, vibe, emoji.
- Edit **USER.md** — who you are, what to call you, context.
- Let the agent fill **MEMORY.md** and **memory/YYYY-MM-DD.md** over time.
- Adjust **HEARTBEAT.md** and **AGENTS.md** if you want different recurring checks or rules.

If you change something that would help others, consider contributing it back to the starter kit (without secrets or personal content).
