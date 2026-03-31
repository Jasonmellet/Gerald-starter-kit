---
name: fractional-cro
description: Autonomous lead generation and revenue optimization for fractional CMO and AI agent builder services. Use when the user needs to find new clients, monitor API costs, or automate outreach for consulting services. Triggers on requests like "find me leads," "CRO help," "new customers," or "monitor my spending."
---

# Fractional CRO

Your autonomous Chief Revenue Officer. Finds leads, tracks opportunities, and keeps your pipeline full while you sleep.

## Core Capabilities

### 1. Lead Discovery
Scans multiple sources for potential clients needing:
- Fractional CMO services
- First AI agent development
- Growth/marketing automation

**Sources:**
- LinkedIn (via Playwright automation)
- Upwork job feeds
- Hacker News "Who's Hiring"
- **X (Twitter)** — lead feed in workspace: `memory/x_lead_feed.json`
- IndieHackers

### X (Twitter) direct lead feed

When the user asks for **new customers** or **leads from X/Twitter**:

1. **Read** `memory/x_lead_feed.json` (in workspace root). It contains recent tweets from search queries like "fractional CMO", "looking for marketing help", "AI agent builder".
2. **Rank** leads by fit (keywords), engagement (likes/replies), and recency. Suggest top 5–10.
3. **Output** for each: @username, why they're a fit, suggested DM or reply (1–2 sentences).
4. If the file is missing or empty: tell the user to run once (or on a schedule):  
   `python3 tools/x_lead_feed.py`  
   They need `X_BEARER_TOKEN` in the repo root `.env`. See `X-LEAD-PLAN.md` for full flow.

**Sending DMs to leads:** If the user wants to reach out on X, they can send a DM with:  
`python3 tools/x_dm.py @username "Your message"`  
Requires OAuth with DM scope (run the X OAuth flow once; see `X-CALLBACK-SETUP.md`).

### 2. Lead Scoring
Ranks opportunities by:
- Budget signals (funding, company size, role seniority)
- Urgency ("immediate," "ASAP," "this week")
- Fit (startup stage, tech-savvy, AI-curious)

### 3. Database Management
SQLite-based lead tracking:
- `leads.db` stores all discovered opportunities
- Tracks status: `new` → `contacted` → `responded` → `meeting` → `closed`
- Prevents duplicate outreach

### 4. Outreach Automation
- Generates personalized pitch templates
- Integrates with user's Playwright LinkedIn automation
- Can queue DMs/emails for manual review

### 5. Cost Monitoring
- Tracks API spend across services
- Alerts on unusual usage patterns
- Suggests optimizations

## Scripts

### `scripts/scrape_linkedin.py`
Searches LinkedIn for target profiles and posts. Requires Playwright setup.

### `scripts/scrape_upwork.py`
Fetches recent job postings matching keywords.

### `scripts/scrape_hn.py`
Monitors Hacker News "Who's Hiring" threads.

### `scripts/score_leads.py`
Analyzes and scores discovered leads.

### `scripts/send_digest.py`
Generates and sends email digest of top opportunities.

### `scripts/init_db.py`
Creates SQLite database schema.

## Usage

**Run full pipeline:**
```bash
python3 scripts/scrape_all.py && python3 scripts/score_leads.py && python3 scripts/send_digest.py
```

**Check specific source:**
```bash
python3 scripts/scrape_upwork.py --keywords "fractional CMO,AI automation"
```

**View lead database:**
```bash
sqlite3 data/leads.db "SELECT * FROM leads WHERE status='new' ORDER BY score DESC LIMIT 10;"
```

## Configuration

Create `config.json` in skill root:
```json
{
  "linkedin": {
    "search_queries": ["fractional CMO", "first marketing hire", "AI automation"],
    "max_results": 50
  },
  "upwork": {
    "categories": ["Marketing Strategy", "AI & Machine Learning"],
    "budget_min": 1000
  },
  "scoring": {
    "budget_weight": 0.4,
    "urgency_weight": 0.3,
    "fit_weight": 0.3
  },
  "digest": {
    "email": "user@example.com",
    "frequency": "daily",
    "min_score": 70
  }
}
```

## Database Schema

See `references/schema.md` for full SQLite schema.

## Integration Notes

- LinkedIn automation requires user's existing Playwright setup
- Email sending uses local SMTP or SendGrid API
- Runs on cron schedule (recommend 2-3x daily)
