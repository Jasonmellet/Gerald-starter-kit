# Plan: Gerald + X (Twitter) for a Direct Line to New Customers

## Goal

Use X (Twitter) to find people who are already talking about problems you solve (fractional CMO, AI agents, marketing automation), then give Gerald a clear role: **read the data → prioritize leads → suggest who to contact and what to say**.

## How Gerald Can Help (Within His Limits)

- **If Gerald has exec:** He can run `python3 tools/x_lead_feed.py` himself (or you can cron it). **If exec is disabled:** He can only read/write/edit files; you (or cron) must run the script to populate `memory/x_lead_feed.json`.
- So the flow is: **something writes X search results into the workspace** (you run a script, or a cron job) → **Gerald reads those files** → summarizes, scores, and suggests outreach (DM templates, who to follow, what to reply to).

## What You Already Have

| Tool | Purpose | Needs |
|------|---------|--------|
| `tools/x_api_client.py` | Search recent tweets, user info, timelines | `X_BEARER_TOKEN` in `.env` |
| `tools/x_monitor.py` | Watch specific users for new tweets | Same |
| `tools/x_scraper.py` | Fetch tweets without API (Nitter) | No token; less reliable |
| `skills/fractional-cro/scripts/scrape_twitter.py` | Nitter-based lead search into `leads.db` | No token |

**Best path for “direct line to customers”:** Use the **X API** (search + user lookup) so you get real-time, structured data. Save results into a file Gerald can read.

## Recommended Flow

### 1. Get an X API bearer token

- [Twitter Developer Portal](https://developer.twitter.com/) → create a project/app → get **Bearer Token** (read-only is enough for search + user lookup).
- Add to `.env`: `X_BEARER_TOKEN=your_bearer_token`

### 2. Run search and save results where Gerald can read them

- **Option A (manual):** When you want leads, run:
  ```bash
  python3 tools/x_api_client.py search "fractional CMO OR \"looking for marketing help\"" --max 20
  ```
  Save the output (or paste into a file), e.g. `memory/x_search_results.txt` or `memory/x_last_search.md`. Then ask Gerald: “Read `memory/x_last_search.md` and tell me the top 5 people to reach out to and what to say.”

- **Option B (scripted):** Use the new **`tools/x_lead_feed.py`** (see below). It runs the same search and writes structured results to `memory/x_lead_feed.json`. You run it (or cron it); Gerald reads `memory/x_lead_feed.json` and suggests outreach.

### 3. Gerald’s job

- Read `memory/x_lead_feed.json` (or whatever file you use).
- Rank by fit (keywords, follower count, recency).
- Output: “Top 5 leads: @user1 because …; suggested DM: …”
- Optionally append a short summary to `memory/` or `outputs/` for your records.

### 4. Optional: Cron for a daily lead feed

- Run `x_lead_feed.py` once per day (e.g. 8am). Gerald can then reference “today’s X lead feed” when you ask “who should I reach out to today?”

## What to Add (Optional)

- **`tools/x_lead_feed.py`** — Wrapper that:
  - Reads search queries from env or a small config (e.g. “fractional CMO”, “AI agent builder”).
  - Calls `x_api_client` search, writes results to `memory/x_lead_feed.json` (tweet text, author username, id, link, optional follower count).
  - So Gerald always has a single file to read for “latest X leads.”

- **Skill or AGENTS.md note** so Gerald knows:
  - “When the user asks for new customers or leads from X/Twitter, read `memory/x_lead_feed.json` (or the file the user names). Summarize and suggest top leads and outreach copy. If the file is missing, tell the user to run: `python3 tools/x_lead_feed.py` (or `python3 tools/x_api_client.py search \"<query>\" --max 20` and save output to `memory/x_last_search.md`).”

---

## Summary

| Step | Who | Action |
|------|-----|--------|
| 1 | You | Add `X_BEARER_TOKEN` to `.env` |
| 2 | You (or cron) | Run `x_api_client.py search "…"` or `x_lead_feed.py` → writes to `memory/` |
| 3 | Gerald | Reads the file, picks top leads, suggests DMs/reply copy |
| 4 | You | Reach out on X (DM, reply, or use the suggested copy elsewhere) |

Gerald becomes your **lead reader and outreach copywriter**; the **direct line** is you running the X search (or cron) and then acting on his suggestions.
