# WORKFLOW.md — Core operating loop

Gerald's default sequence for tasks:

1. **Understand task** — Clarify what is being asked; if ambiguous, ask the user.
2. **Check project skills first** — Look in `.cursor/skills/` for a matching workflow and follow its `SKILL.md` if applicable.
3. **Determine required files** — Identify which files to read (and whether to write or edit).
4. **Read files** — Use the read tool for each relevant file. Do not assume contents.
5. **Reason about content** — Analyze what was returned by the tools.
6. **Produce output** — If the task requires it, use write or edit with the appropriate path and content.
7. **Log activity** — Update LOGBOOK.md with timestamp, task, files read, files written, result, and any notes.

See **TOOLS.md** for tool rules and the file task protocol.

---

## YouTube analysis (Phase 1)

When the user asks to analyze a YouTube video:

1. Call `exec` with `python3 tools/youtube_ingest.py "<URL>"` using the exact URL the user provided.
2. Read the new `*_metadata.json` and `*_transcript.txt` files in `sources/`; do not assume their contents.
3. Synthesize themes, advice, and recommendations from the transcript.
4. Write an analysis file to `outputs/` using the structure in `templates/youtube-analysis-template.md`.
5. Append an entry to `LOGBOOK.md`.

If ingest fails or no transcript exists in `sources/` for the video, do not claim to have analyzed it; say clearly what failed. See **YOUTUBE-WORKFLOW.md** for full steps.

---

## Daily review

At least once per day, or when asked to "review yourself" or "clean things up":

1. Read the core files: `AGENTS.md`, `MEMORY.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`.
2. Check for stale instructions, contradictions, missing context, and lessons that should be written down.
3. Update the right file directly instead of leaving the fix implied.
4. Add a short review note to `LOGBOOK.md`.
