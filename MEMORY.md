Long-term memory for Gerald. Update when significant events or decisions occur.

## 2026-03-06 — First Session with Jason

**Key Events:**
- Transcribed and analyzed Matthew Berman's "I figured out the best way to run OpenClaw" video
- Discussed meeting transcription workflow using Recall.ai
- User previously had agent "Pepper" using Recall.ai for transcription and customer classification
- Agreed to build a skill for meeting transcription with post-processing for customer mention extraction
- User cloned OpenClaw for his wife to use

**Decisions Made:**
- Will not use cloud transcription for classified data; confirmed current use case is strategy calls only (no classified info)
- Will build Recall.ai integration with local post-processing
- Need to set up daily maintenance workflow (per Matthew Berman video recommendations)

## 2026-03-11 — Meeting Transcription System Completed

**Key Events:**
- Built complete meeting transcription integration with Recall.ai
- Gmail OAuth, Recall.ai client, meeting orchestrator, iCal parsing, transcript API all working
- LaunchAgent and setup script created
- Summary emails functional

**Decisions Made:**
- System runs continuously to auto-join meetings
- Daily digest emails at 9am with X monitor findings

## 2026-03-19 — Daily Maintenance Review

**Status:**
- All core systems operational
- X monitoring active (daily at ~$0.11/day)
- Task reminder system checking TASKS.md deadlines
- Security review scheduled weekly (Mondays 9am)
- CRO skill monitoring Upwork/X API approvals every 2 days

## 2026-03-24 — Business Memory Direction

**Key Decision:**
- Jason clarified that the goal is better long-term memory and pattern recall, not building unnecessary new infrastructure.

**What to remember going forward:**
- Favor lightweight memory discipline over overbuilt systems unless a larger build is clearly needed.
- Preserve recurring business patterns, strategic preferences, promising opportunity areas, and persistent blockers.
- Store the signal, not the whole conversation: remember what will improve the next decision, not just what happened.

**Recurring opportunity areas worth retaining:**
- Meeting intelligence and customer insight extraction
- AI workflow automation
- Agent-assisted business operations
