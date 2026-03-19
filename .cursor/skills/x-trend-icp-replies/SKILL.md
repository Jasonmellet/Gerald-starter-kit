---
name: x-trend-icp-replies
description: Research trending X/Twitter posts and recommend topic opportunities aligned to the ICP, then draft human-sounding reply angles and sample responses. Use when the user asks to find trends on X, identify reply opportunities, generate responses to real posts, or prioritize topics likely to drive relevant conversations.
---

# X Trend ICP Replies

## Purpose

Use this skill to turn X/Twitter trend research into actionable reply opportunities that match the ICP and produce real person style responses.

## Inputs

Collect or confirm:
- Trend source from X API data
- Time window (default: last 24-72 hours)
- Topic scope (default: B2B growth, pipeline, RevOps, founder-led GTM)
- Number of opportunities requested (default: 10)

## Required context

Read these files before scoring opportunities:
- `docs/x-icp-definition.md`
- `docs/x-content-brief.md`
- `docs/reference/x-automation-rules.md`

## Workflow

1. Gather candidate posts
   - Pull current high-signal posts from X API data.
   - Prefer posts with clear operator pain, disagreement, or practical implementation discussion.
2. Filter for compliance and relevance
   - Keep only posts where replying is appropriate under `docs/reference/x-automation-rules.md`.
   - Remove low-context memes, broad news with no operator angle, and engagement bait.
3. Score each post (1-5 per dimension)
   - ICP fit: matches founder/CEO, RevOps leader, growth operator context
   - Pain clarity: problem is specific and tangible
   - Reply leverage: strong chance a thoughtful response advances conversation
   - Authority fit: allows concrete operational insight
   - Timeliness: trend momentum is active now
4. Select top opportunities
   - Keep highest total scores with topic diversity.
   - Avoid near-duplicates of the same trend.
5. Generate suggested responses
   - Use a friendly, practical tone.
   - Give one concise "why now" explanation, one angle, and 2 sample replies per post:
     - one short reply
     - one medium-depth reply
   - Keep language human and specific, not generic.

## Output format

Use this structure:

```markdown
# X Trend Opportunities (ICP-Aligned)

## Snapshot
- Time window: <value>
- Candidate posts reviewed: <n>
- Opportunities selected: <n>

## Top opportunities

### 1) <topic label>
- Post: <url>
- Author: <handle + role if known>
- Why this is trending now: <1-2 lines>
- ICP fit: <Primary/Secondary + rationale>
- Pain signal: <specific pain in post>
- Suggested angle: <friendly, operator-level POV>
- Sample reply (short): "<text>"
- Sample reply (medium): "<text>"

### 2) <topic label>
...

## Suggested follow-up themes
- <theme 1>
- <theme 2>
- <theme 3>
```

## Quality checks

Before finalizing:
- Ensure every selected post maps to ICP criteria from `docs/x-icp-definition.md`.
- Ensure replies stay practical and human, with no hype language.
- Ensure suggestions align with `docs/x-content-brief.md` constraints.
- Exclude outreach patterns that would violate `docs/reference/x-automation-rules.md`.

## Fallback behavior

If live X API trend data is unavailable:
- Ask for exported post URLs or a timeline dump.
- Run the same scoring and output format on provided posts.
