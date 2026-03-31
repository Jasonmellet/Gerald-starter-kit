## X Growth Loop — Build Tracker

**Goal:** Build a compliant X growth loop that turns posts into comments, comments into conversations, and conversations into qualified DMs.

### Activity log

- [x] 2026-03-13 — Implement `tools/x_post.py` (create + delete via X API) and send/delete a test post (`2032526257468952862`).
- [x] 2026-03-13 — Run one-off test script `tools/x_test_post.py` to publish \"Gerald automation test #1\" via X API v2 (tweet ID `2032530013572985142`).
- [x] 2026-03-13 — Fetch 10 most recent posts via `tools/x_test_timeline.py` using GET `/2/users/:id/tweets` and confirm the test post (`2032530013572985142`) appears.
- [x] 2026-03-13 — Delete test post `2032530013572985142` via `tools/x_test_delete.py` using DELETE `/2/tweets/:id` and confirm removal with a follow-up GET.
- [x] 2026-03-13 — Retrieve replies to tweet `2032259783844122869` via `tools/x_test_replies.py` using recent search (query `conversation_id:<id> is:reply`) and print username, user ID, and reply text.
- [x] 2026-03-13 — Post a one-off reply to tweet `2032259783844122869` via `tools/x_test_reply.py` using POST `/2/tweets` with reply.in_reply_to_tweet_id and log returned reply ID `2032531172232745209`.
- [x] 2026-03-13 — Send a one-time DM via `tools/x_test_dm.py` using POST `/2/dm_conversations/with/:participant_id/messages` to user `1866197125391958016`, logging dm_event_id `2032531534524063798`.
 - [x] 2026-03-13 — Send friendly DM to @Bearseoservice (user `1834798100407312384`) via `tools/x_test_dm.py` with custom text asking what he's working on, logging dm_event_id `2032532011512934759`.
 - [ ] 2026-03-13 — Attempt to fetch recent DMs via `tools/x_test_dm_fetch.py` using DM conversation endpoint (`GET /2/dm_conversations/{id}/messages`), but X API returned 404 (DM read not available for this app/tier); no messages could be listed. _(Status: blocked by current app/tier; keep as known limitation.)_
- [ ] 2026-03-13 — Implement `tools/x_test_dm_events.py` to call `GET /2/dm_events` (requires OAuth2 user token). Current state: `X_USER_ACCESS_TOKEN` present but X returned 401 Unauthorized for `/2/dm_events` — likely app permission/tier limitation on DM read; DM write remains working. _(Status: blocked by current app/tier.)_
- [ ] 2026-03-13 — Implement `tools/x_test_dm_event_get.py` to call `GET /2/dm_events/{event_id}` with a known dm_event_id (`2032532011512934759`), but X again returned 401 Unauthorized — confirms DM read endpoints are not permitted for this app/tier even with valid OAuth2 user token. _(Status: blocked by current app/tier.)_
 - [x] 2026-03-13 — Extract unique user IDs from replies to tweet `2032259783844122869` via `tools/x_test_reply_user_ids.py` (reusing conversation search) and print list to console (`1834798100407312384`, `1866197125391958016`).
 - [x] 2026-03-13 — Run one-time pipeline test via `tools/x_test_pipeline.py`: post pipeline test tweet (ID `2032545267346493952`) tagging @Bearseoservice and @TimoBuilds_, wait 60s, search for replies, and log that no replies were found yet so the reply+DM steps were skipped for this run.
 - [x] 2026-03-13 — Explore "trending" topics via `tools/x_test_trending.py` using `/2/tweets/search/recent`, first on query `\"ai agents\"` (showing high-RT Polymarket thread) then `(ai agents) -is:retweet` to surface top non-retweet posts and their engagement metrics.
- [x] 2026-03-13 — Update `tools/x_post.py` to always use OAuth 1.0a credentials for posting (since `X_USER_ACCESS_TOKEN` returns 401 for `POST /2/tweets`) and successfully publish strong-opinion agents post (tweet ID `2032549586066141653`).
 - [x] 2026-03-13 — Run `tools/x_handle_replies_once.py` for pipeline tweet `2032545267346493952`: detect latest reply from @Bearseoservice (tweet `2032549067914453481`), post contextual reply (`2032550190591181226`), and send follow-up DM (dm_event_id `2032550195024568546`).

---

### Phase 1 — Strategy + guardrails

- [ ] Define niche, voice, and target audience.
- [ ] Define what counts as a “good lead”.
- [ ] Define what topics you want to be known for.
- [ ] Define what you will never post or DM.
- [ ] Write hard compliance rules for Gerald.
- [ ] **Only use the X API, never browser scripting.**
- [ ] Never auto-like.
- [ ] Never bulk follow or unfollow.
- [ ] Never reply to strangers based on keyword search alone.
- [ ] Never send unsolicited DMs.
- [ ] Require user intent before reply/DM automation.
- [ ] Add opt-out language for DMs and automated follow-up.

### Phase 2 — Tracking system

- [ ] Build a list of accounts to monitor daily.
- [ ] Split tracked accounts into tiers (Tier 1/2/3).
- [ ] Track which posts from those accounts get strong engagement.
- [ ] Track topic patterns.
- [ ] Track hook patterns.
- [ ] Track formatting patterns.
- [ ] Track CTA patterns.
- [ ] Save winning examples in a swipe file.
- [ ] Score posts by likes, comments, reposts, and relevance.

### Phase 3 — Topic research

- [ ] Pull top-performing posts from tracked accounts each day.
- [ ] Identify recurring themes.
- [ ] Identify what people are arguing about.
- [ ] Identify what people are confused about.
- [ ] Identify what people are asking for help with.
- [ ] Identify what is getting unusually high replies.
- [ ] Turn those patterns into post angles.
- [ ] Avoid copying wording too closely.
- [ ] Create original takes, not clones.
- [ ] Prioritize topics that naturally invite comments.

### Phase 4 — Content engine

- [ ] Generate a daily batch of post ideas.
- [ ] Create posts in multiple styles (strong opinion, contrarian, how-to, story, simple list).
- [ ] Build each post around one core goal (awareness, engagement, qualification, DM trigger).
- [ ] Add a clear CTA when needed (“Comment X”, “Tell me where you’re stuck”, “Want the framework?”).
- [ ] Keep posts native to X style.
- [ ] Queue several posts for the day and space them out.
- [ ] Avoid duplicate or near-duplicate posting.

### Phase 5 — Review + safety checks before posting

- [ ] Check for duplication.
- [ ] Check for spammy phrasing.
- [ ] Check for misleading claims.
- [ ] Check for sensitive or risky language.
- [ ] Check that links are clean and not deceptive.
- [ ] Check that the CTA does not mislead users.
- [ ] Check that the post does not overpromise.
- [ ] Approve or reject each post.
- [ ] Send approved posts through Cursor using the API.

### Phase 6 — Publishing workflow

- [x] Publish post 1 (via `tools/x_test_post.py`) and additional strong-opinion post (via `tools/x_post.py`).
- [ ] Log post ID, time, topic, hook, and CTA.
- [ ] Publish additional posts later in the day.
- [ ] Track performance by time slot.
- [ ] Track which CTA drives comments best.
- [ ] Track which topic drives the best replies.
- [ ] Pause low-performing patterns.
- [ ] Double down on high-performing ones.

### Phase 7 — Comment monitoring

- [x] Watch each post for replies and comments (tested via search + one-off handlers).
- [ ] Detect who engaged first.
- [ ] Confirm that the interaction gives you permission to reply.
- [ ] Classify each responder (warm lead, curious person, fan, troll, spam).
- [ ] Ignore trolls and spam.
- [ ] Prioritize warm leads and real curiosity.

### Phase 8 — Automated reply layer

- [ ] Reply only after the user has engaged with your post.
- [ ] Send one useful reply per interaction.
- [ ] Keep replies contextual to their comment.
- [ ] Ask an easy follow-up question when appropriate.
- [ ] Try to extend the conversation naturally.
- [ ] Do not blast generic repeated replies.
- [ ] Do not reply to random platform users who never engaged with you.
- [ ] Keep reply templates varied.
- [ ] Add safety filters for profanity, hate speech, and risky content.
- [ ] Log every automated reply.

### Phase 9 — DM trigger logic

- [ ] Only DM when the user has clearly shown intent.
- [ ] Encode “good signals” (asked for framework, said “send it”, asked a direct question, mentioned wanting help).
- [ ] Do not DM every commenter blindly.
- [ ] Create DM eligibility rules (high-intent vs low-intent).
- [ ] Trigger one DM only.
- [ ] Include a clear opt-out line.
- [ ] Keep the first DM short, relevant, and expected.

### Phase 10 — DM conversation flow

- [ ] Start with context from the public comment.
- [ ] Deliver the promised thing first.
- [ ] Ask one light qualifying question.
- [ ] Identify intent level (learning, exploring, buying, not a fit).
- [ ] Route each person into the right path.
- [ ] Give value, continue conversation, offer next step.
- [ ] Stop messaging if they disengage; do not keep sending follow-up DMs without permission.

### Phase 11 — Lead handling

- [ ] Create lead tags (hot, warm, cold, not a fit).
- [ ] Save conversation notes.
- [ ] Save source post.
- [ ] Save topic of interest.
- [ ] Save objections.
- [ ] Save next step.
- [ ] Route hot leads to manual review or sales workflow.
- [ ] Keep CRM or lead sheet updated.

### Phase 12 — Metrics

- [ ] Track post volume, impressions, likes, comments, comment rate, reply rate, DM rate, DM response rate, qualified lead rate, booked-call rate, blocked/negative-response rate, opt-outs.
- [ ] Review metrics daily.
- [ ] Review metrics weekly.
- [ ] Kill weak patterns fast.

### Phase 13 — Optimization loop

- [ ] Review top-performing posts every day.
- [ ] Review which hooks cause the most comments.
- [ ] Review which reply styles extend conversation.
- [ ] Review which DM openers get responses.
- [ ] Review which topics attract buyers vs spectators.
- [ ] Update prompts and templates weekly.
- [ ] Expand tracked account list over time.
- [ ] Keep testing new angles.
- [ ] Keep a live library of winners.

### Phase 14 — Human-in-the-loop controls

- [ ] Decide auto-post boundaries (what can run fully automated).
- [ ] Define auto-reply limits.
- [ ] Lock down DM rules for strict compliance.
- [ ] Flag high-risk conversations for manual review.
- [ ] Flag potential buyers for manual takeover.
- [ ] Pause automations if negative signals spike.
- [ ] Add daily fail-safe checks.

### End-to-end checklist (build order)

1. [ ] Define niche and audience (Phase 1).
2. [ ] Write compliance rules and guardrails for Gerald (Phase 1).
3. [ ] Build tracked-account list + tiers (Phase 2).
4. [ ] Implement daily research pull from tracked accounts (Phases 2–3).
5. [ ] Identify high-engagement topics and patterns (Phase 3).
6. [ ] Turn topics into original post angles in your voice (Phase 3).
7. [ ] Generate daily post batch with mixed styles and goals (Phase 4).
8. [ ] Run safety and duplication checks pre-publish (Phase 5).
9. [ ] Publish through Cursor using the API and log posts (Phase 6).
10. [ ] Monitor comments and classify responders (Phases 7–8).
11. [ ] Send compliant public replies only to engaged users (Phase 8).
12. [ ] Trigger DMs only for clear-intent users with opt-out (Phase 9).
13. [ ] Deliver value in DM first and qualify leads (Phases 9–10).
14. [ ] Route leads to next step and keep CRM/lead sheet updated (Phase 11).
15. [ ] Log all actions, measure results, and review regularly (Phase 12).
16. [ ] Optimize prompts, templates, and account list weekly (Phase 13).
17. [ ] Maintain human-in-the-loop controls and fail-safes (Phase 14).

