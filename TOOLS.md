# TOOLS.md — Tool discipline

Gerald has **read**, **write**, **edit**, and **exec**. Use them according to these rules.

## Tool rules

- **Always use the read tool before reasoning about file contents.** Do not assume or guess what a file contains; call read and use the returned content.
- **Never assume file contents.** If you have not read a file in this session, do not state its contents.
- **Use write only when explicitly instructed** to create or update a file (e.g. "write a summary to summary.md").
- **Use edit for modifying existing files** when the user asks for a change to content that already exists.
- **Never describe an action that was not actually executed.** Only report what you did via real tool calls. If you did not call read/write/edit, do not claim you did.

## File task protocol (step-by-step)

1. **Call read** on each relevant file.
2. **Analyze contents** using the data returned by the tools.
3. **Synthesize result** (e.g. summary, answer).
4. **Call write or edit** if the task requires creating or changing a file.
5. **Report what actually happened** — which files were read, what was written or edited, and any errors. Do not invent or simulate tool use.

See **TOOL-USE.md** for more detail on read/write usage and paths.

---

## YouTube analysis tasks

For YouTube analysis (see **YOUTUBE-WORKFLOW.md**):

1. **First** call **exec** with command `python3 tools/youtube_ingest.py "<URL>"` (the URL the user gave). Do not reply with text only — call exec first.
2. **Then** use **read** on the new transcript and metadata files in `sources/` (created by the script).
3. **Then** use **write** to create the analysis markdown in `outputs/` (based on `templates/youtube-analysis-template.md`).
4. **Then** append a row to LOGBOOK.md.

**Strict rule:** Do not summarize or analyze a YouTube video unless you have actually run the ingest (exec) and a transcript file exists in `sources/`. If the exec fails (e.g. no captions), say so clearly; do not pretend to have analyzed the video.
