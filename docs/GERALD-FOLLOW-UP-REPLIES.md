# Gerald: follow-up replies (waterfall)

After we send a DM to a prospect (in a run), we optionally wait a few minutes then post a **public reply** to their latest tweet. That’s the “follow-up reply” step.

**X’s official Automation Rules** (opt-in, one reply per interaction, reply to their post) are captured in **docs/reference/x-automation-rules.md** — treat that as the bible for what’s allowed.

## What worked: the one successful reply (Timo, run 8)

We had **one** recorded successful follow-up reply: **@TimoBuilds_** (run 8). For that contact we:

1. Sent a DM (run 8).
2. Waited `follow_up_reply_delay_seconds` (e.g. 5 min).
3. Fetched Timo’s latest tweet, generated a short question with the LLM, called `POST /2/tweets` with `reply.in_reply_to_tweet_id`.
4. X accepted it; we stored `reply_tweet_id` on that contact.

**Why it worked:** Per X’s Automation Rules, automated replies are allowed when the user has **opted in** (e.g. **replied to your post** or **sent you a DM**); one reply per interaction; reply to their post. The API 403 (“not mentioned or otherwise engaged”) enforces the same idea. So for Timo, X likely saw that condition as met. We don’t store “why” in the DB; we only know the request format and auth are correct and that we waterfall when we get 403.

## Replicating: reply waterfall

We can’t assume every contact will get a successful reply. So we use a **waterfall**, like we do for DMs:

1. **Eligible** = contacts in the run with `send_status == 'sent'`, no `reply_tweet_id` yet, and no `reply_skipped_reason` (so we don’t retry people X has already blocked).
2. For each contact: fetch latest tweet → generate question → `create_reply(...)`.
3. **If reply succeeds:** set `reply_tweet_id`, count `replies_sent`, move on.
4. **If X returns 403 “reply not allowed” (mention/engage policy):** set `reply_skipped_reason = 'x_policy'` on that contact so we **don’t retry** next run, count `skipped_reply_policy`, **continue to the next contact**.
5. **Other failures** (no tweet, no question, auth/network): count `failed` or `skipped_*`, continue.

So we never stop the batch on one failure; we move on to the next. Policy-blocked contacts are marked once and skipped in future runs.

## Summary counts

After `send_replies_for_run` we report:

- `contacts_eligible` — how many we considered
- `replies_sent` — replies that posted
- `skipped_no_tweet` — no tweet to reply to
- `skipped_no_question` — LLM didn’t produce a question
- `skipped_reply_policy` — X 403 (we marked them, won’t retry)
- `failed` — other errors

See also: **docs/reference/x-api-manage-posts.md** (API payload, 403 behavior), **docs/reference/x-automation-rules.md** (X Automation Rules bible).
