# YOUTUBE-WORKFLOW.md — Phase 1 captions-first analysis

**CRITICAL — Do this first:** When the user asks you to transcribe, analyze, or get feedback on a YouTube video and gives you a URL, your **very next response MUST be a tool call**: call the **exec** tool with the command below. Do **not** send a text-only reply like "I'll fetch it" or "Let me get that for you." Call exec first. Then, after the tool returns, continue with read → write → log.

**Rule:** Never claim a transcript was retrieved if it was not actually retrieved. If subtitles/captions are unavailable, say so clearly.

---

## 1. Run the ingest (you have exec) — call this tool immediately

Use the **exec** tool to run the ingest script with the user's URL. Command (use the exact URL the user gave):

```
python3 tools/youtube_ingest.py "https://www.youtube.com/watch?v=..."
```

- **workdir:** workspace root (default).
- **command:** `python3 tools/youtube_ingest.py "<URL>"` with the real URL in quotes.

The script writes into `sources/`:
- `sources/<slug>_metadata.json` — title, channel, date, etc.
- `sources/<slug>_transcript.txt` — captions/subtitles

If the exec output shows an error (e.g. "No captions/subtitles available"), stop and tell the user: "No transcript was retrieved for this video (captions/subtitles unavailable). Phase 1 does not support audio transcription."

---

## 2. Read the created files

After a successful run, use **read** on:
- The metadata file in `sources/` (name ends with `_metadata.json`).
- The transcript file in `sources/` (name ends with `_transcript.txt`).

If you don't know the slug, list or read the most recently created files in `sources/` (the script creates one metadata and one transcript per run).

---

## 3. Write the analysis

Use **write** to create an analysis file in `outputs/`:
- Base the structure on `templates/youtube-analysis-template.md`.
- Fill in all sections using the metadata and transcript you read.
- Filename example: `outputs/<slug>-analysis.md`.

Include: core theme, key ideas, advice/recommendations, what applies to their systems, caveats, action items, and your notes (transcript file, metadata file, analysis date).

---

## 4. Log and reply

- Append one row to **LOGBOOK.md**: timestamp, task (e.g. "YouTube analysis: [video title]"), files read, files written, result, notes.
- Reply to the user with a short summary and where the analysis was written (e.g. `outputs/<slug>-analysis.md`).

---

## 5. Optional

If the analysis suggests follow-up work, add items to **Ideas / Future Tasks** in TASKS.md.

---

## If captions are unavailable

- The ingest script exits with an error and does not create transcript files.
- Do not summarize or analyze the video without a transcript in `sources/`.
- Tell the user: "No transcript was retrieved for this video (captions/subtitles unavailable). Phase 1 does not support audio transcription. I can only analyze when a transcript exists in sources/."
