# TOOL-USE.md — How You Work With Files and Commands

You have **read**, **write**, **edit**, and **exec** tools. When the user asks you to read, write, or run something, you **must use these tools**. Describing in chat is not enough.

## Rule

**If the user asks you to read files or write something to a file, you MUST call the tools.**  
Do not reply with "I'll read..." or "Here's what I found..." unless you have **already** called the `read` tool for those files and (if asked to write) the `write` tool. A reply that only describes what you would do is a failed task.

## YouTube: you MUST call exec first

**If the user asks you to transcribe or analyze a YouTube video and provides a URL,** your next message MUST be a **tool call** — the **exec** tool with this command (use the exact URL they gave):

`python3 tools/youtube_ingest.py "<URL>"`

Do **not** reply with text only (e.g. "I'll fetch it" or "Let me process that"). Call the exec tool first. After it returns, then use read on the new files in sources/, then write the analysis to outputs/, then log.

## Protocol for "read files and write a summary"

1. Call **read** for each file (e.g. `notes.md`, `ideas.txt`, `sample.csv`).
2. Wait for the tool results. Use the **actual content** returned.
3. Call **write** with the path (e.g. `summary.md`) and the summary text.
4. Then you may send a short chat message confirming you did it.

## Protocol for "read this file" or "what's in X?"

1. Call **read** with the file path.
2. Use the content the tool returns in your reply. Do not invent or guess the contents.

## Protocol for "write X to file Y"

1. Call **write** with the path and the content.
2. Then confirm in chat.

## Protocol for "set up a cron job" or "create an automation"

1. Use **write** or **edit** to create/update the script or crontab *file* (e.g. a `.sh` script or a file with cron lines).
2. In your reply, **do not** say the automation is "installed" or "active". Say you created the files and give the **exact command** the user must run to activate (e.g. `bash tools/install_cron.sh` or “Run `crontab -e` and add these lines: …”).

## Paths

All paths are in this workspace. Use simple names: `notes.md`, `ideas.txt`, `sample.csv`, `summary.md`. No leading slashes or full paths needed for files in the workspace root.

---

**Remember:** Your message is not the deliverable. The file content (from read) and the written file (from write) are. Use the tools first.
