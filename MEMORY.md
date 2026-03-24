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

## 2026-03-24 — First Business Memory Entries

**Durable business context:**
- Created `BUSINESS-MEMORY.md` as a lightweight place for important clients, contacts, and recurring business context.
- First client entries: Boar Blanket and HogEye Cameras.
- Both accounts come through Casey Fuerst at Tic Tac Toe Marketing Agency, an important repeat-work source Jason has worked with for about 1 year.
- Boar Blanket work includes SEO, content creation, blueprint/strategy, and 5 blog posts per month published to WordPress draft status around the 20th.
- HogEye Cameras is a similar SEO/content account, but content goes to Google Docs for approval around the 20th instead of directly into WordPress.
- Important commercial context: Boar Blanket and HogEye Cameras together currently pay **$750 USD/month total** for **10 pieces**, and HogEye Cameras has a major approval bottleneck that can delay approvals for months.
- Added Camp Lakota as another content client: **$1,250 USD/month** for **10 pieces**, sourced through Stephanie Fox at Fox Consulting, with Hannah as the client contact.
- Camp Lakota uses a more efficient direct publishing workflow through the WordPress REST API from one of Jason's repos via Cursor.ai.
- Added Theo Transformation Advisory as a higher-value account through Phil Ayres at Ron Media Partners.
- Theo includes **$2,500/month** for custom email outreach plus lead sourcing/enrichment, and **about $1,250/month** more for a 10-piece recurring content package including publishing.
- Added Stoneford as a new Casey/TTT client on a **3-month contract** at **$2,000/month** for church lead sourcing in Virginia and Florida plus building an email outreach system.
- Stoneford uses Jason's own stack: Spiffy for Google Maps lead crawling/enrichment and a custom-built outreach tool for emailing.
- Important pattern: higher-value work includes custom outreach/revenue services and Jason's own systems leverage, not just low-priced content production alone.
