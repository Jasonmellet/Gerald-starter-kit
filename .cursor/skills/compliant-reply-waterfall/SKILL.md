---
name: compliant-reply-waterfall
description: Execute and troubleshoot policy-compliant follow-up reply workflows on X using waterfall behavior and skip markers for blocked contacts. Use when the user asks about automated follow-up replies, X reply 403 policy errors, or safe one-reply-per-interaction operations.
---

# Compliant Reply Waterfall

## Use when

- User asks to send or debug follow-up replies
- X API returns reply-policy 403 errors
- User asks how to keep replies compliant and avoid retries on blocked contacts

## Required reads

- `docs/GERALD-FOLLOW-UP-REPLIES.md`
- `docs/reference/x-automation-rules.md`
- `docs/reference/x-api-manage-posts.md`

## Waterfall logic

1. Build eligible set
   - Contacts with successful prior send
   - No existing `reply_tweet_id`
   - No permanent skip reason already recorded
2. Attempt reply per contact
   - Fetch latest eligible post
   - Generate concise question/angle
   - Create reply with `reply.in_reply_to_tweet_id`
3. Handle outcomes
   - Success: save reply ID and move on
   - Policy 403 ("not mentioned or otherwise engaged"): mark skip reason `x_policy`, continue
   - Other failure: record failure code, continue
4. End-of-run summary
   - Report eligible, sent, skipped-policy, skipped-no-tweet, skipped-no-question, failed

## Compliance constraints

- Follow opt-in intent rules and one-reply-per-interaction guidance in `docs/reference/x-automation-rules.md`.
- Never batch-send unsolicited replies when user intent is not established.
- Respect API restrictions even if manual web replies might appear to work.

## Output format

```markdown
# Follow-Up Reply Run

- Contacts eligible: <n>
- Replies sent: <n>
- Skipped policy: <n>
- Skipped no tweet: <n>
- Skipped no question: <n>
- Failed: <n>

## Notable outcomes
- <success or failure examples>

## Compliance notes
- <policy checks applied>

## Next step
- <single recommended action>
```

## Guardrails

- Do not retry contacts already marked policy-blocked unless user explicitly requests a manual re-check.
- Do not claim compliance without referencing the rules file and observed interaction context.
