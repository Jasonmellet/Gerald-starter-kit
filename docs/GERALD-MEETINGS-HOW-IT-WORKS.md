# How the meeting infrastructure becomes part of Gerald

You have two “Gerald” layers that work together:

---

## 1. Gerald the notetaker (automation)

- **What it is:** A scheduled process (LaunchAgent runs `meeting_orchestrator.py --once` every 5 minutes).
- **Identity:** Uses `gerald@allgreatthings.io` (Gmail), and the Recall bot is named **“Gerald (Notetaker)”**. So in the meeting and in the inbox it’s “Gerald.”
- **What it does:** Polls Gmail for invites → joins when the meeting is in the 15‑minute window → Recall records and transcribes → when the meeting is done, the orchestrator gets the transcript, runs the meeting processor, saves to `memory/meetings/`, sends you the summary email from gerald@allgreatthings.io, and appends a line to `memory/YYYY-MM-DD.md`.

So **operationally** it’s Gerald: same name, same email, same “I was in the call and I’m emailing you the summary.”

---

## 2. Gerald the agent (you talk to him in Cursor)

- **What it is:** The agent that reads SOUL.md, MEMORY.md, AGENTS.md, `memory/YYYY-MM-DD.md`, etc., and uses file tools (read/write/edit) and skills.
- **How meetings become part of him:**
  - **Daily memory:** After each meeting the orchestrator appends to `memory/YYYY-MM-DD.md` a line like:  
    `- **Meetings:** Attended "Meeting Name"; summary emailed to jason@allgreatthings.io.`  
    So when Gerald (the agent) does his “Every Session” read of **today’s** daily note, he sees that **he** (his notetaker side) attended a meeting and sent the summary. It’s in his continuity.
  - **Meeting summaries on disk:** All summaries (and analyses) live in **`memory/meetings/`**. That’s in the same memory namespace as his daily and long‑term memory. So when you ask “what happened in my meetings?” or “summarize last week’s calls,” he can **read** `memory/meetings/` and answer. AGENTS.md now tells him that meeting summaries live there and that he attends as the notetaker.
  - **Skill:** `skills/meeting-transcription/SKILL.md` tells him how the meeting system works (orchestrator, Recall, Gmail, where things are saved, how to send a meeting summary email). So he can explain it and, if given tools, run or troubleshoot it.

---

## 3. How they connect

| Piece | Who uses it |
|--------|--------------|
| **Same identity** | Notetaker = “Gerald” in the call and in email; agent = “Gerald” in chat. One persona. |
| **memory/meetings/** | Written by the orchestrator; read by the agent when you ask about meetings. |
| **memory/YYYY-MM-DD.md** | Orchestrator appends one line per meeting; agent reads it as part of his daily notes, so he “remembers” he attended. |
| **meeting-transcription skill** | Agent uses it to explain and reason about the meeting pipeline. |

So: the infrastructure **is** Gerald’s notetaker side. It writes into **his** memory (`memory/meetings/`, `memory/YYYY-MM-DD.md`), and the agent you talk to is instructed to treat those as **his** meetings and **his** summaries. One setup, one name, one memory space.
