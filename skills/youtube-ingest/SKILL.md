---
name: youtube-ingest
description: Transcribe and analyze a YouTube video from a URL. Use when the user asks to transcribe, analyze, or get feedback on a YouTube video and provides a URL. When this applies, you MUST call the exec tool first — do not reply with text only.
---

# YouTube Ingest — Transcribe and Analyze

**Prerequisites (already in workspace):** `tools/yt-dlp_macos` and `tools/youtube_ingest.py` are present. Do not tell the user to install yt-dlp or ffmpeg — the script uses the bundled binary. Just call exec.

**When the user gives you a YouTube URL and asks to transcribe or analyze it, your next action MUST be a tool call.**

1. **Call the exec tool immediately.** Do not send a chat message first. Use this exact command (replace with the user's URL):
   ```
   python3 tools/youtube_ingest.py "https://www.youtube.com/watch?v=..."
   ```
   Workdir is the workspace (default).

2. If exec fails (e.g. "No captions/subtitles available"), tell the user and stop.

3. If exec succeeds, **read** the new files in `sources/` (they end with `_metadata.json` and `_transcript.txt`).

4. **Write** an analysis to `outputs/<slug>-analysis.md` using the structure in `templates/youtube-analysis-template.md`.

5. Append one row to **LOGBOOK.md**, then reply to the user with a short summary.

**Rule:** Do not say "I'll fetch it" or "Let me process that" without calling exec. Call the exec tool first.
