---
name: self-improvement
description: Research and monitor trends to improve Gerald's capabilities. Uses DataForSEO for SERP search, trends, and content analysis. $10/month budget with full audit logging.
---

# Self-Improvement Research Skill

Proactive research to discover new tools, techniques, and best practices for AI agents and marketing automation.

## Overview

This skill allows Gerald to:
- Search the web via DataForSEO SERP API
- Monitor trends for AI agents, OpenClaw, and marketing automation
- Discover new tools and techniques
- **Budget: $10/month with full audit logging**

## Safeguards

### Spend Limits
- **Monthly cap:** $10 (configurable)
- **Hard stop:** 500 API calls/month (~$0.02/call)
- **Daily limit:** 20 calls max
- **Per-query limit:** $0.50 max

### Audit Trail
All API calls logged to:
- `memory/api-usage/YYYY-MM-DD.json` — daily detailed logs
- `memory/api-usage/spending.json` — running totals
- Weekly email digest of activity

### Safe Queries Only
- Read-only searches (no posting, no account actions)
- Public data only
- No competitive espionage beyond public SERPs

## Setup

✓ Credentials in `.env`:
```
DATAFORSEO_LOGIN=jason@allgreatthings.io
DATAFORSEO_PASSWORD=5f1e1593f76852c2
DATAFORSEO_LOCATION_CODE=2840
DATAFORSEO_LANGUAGE_CODE=en
```

✓ Budget configured: $10/month

## Usage

### Run Research Query
```bash
python3 tools/research_agent.py --query "OpenClaw AI agent improvements"
```

### Check Current Spending
```bash
python3 tools/research_agent.py --status
```

### Daily Trend Check (automated)
```bash
python3 tools/research_agent.py --trends
```

## Research Topics

Default monitoring queries:
1. **OpenClaw ecosystem** — new skills, updates, best practices
2. **AI agent automation** — techniques, tools, frameworks
3. **Marketing automation** — cold email, PPC, SEO trends
4. **LLM improvements** — new models, prompting techniques

## Cost Breakdown

| Endpoint | Cost per 100 calls | Typical Use |
|----------|-------------------|-------------|
| SERP API | ~$2.00 | Search results, featured snippets |
| Trends API | ~$1.50 | Search trend data |
| Keywords API | ~$1.00 | Keyword research |

At $10/month = ~400-500 API calls

## File Structure

```
skills/self-improvement/
  SKILL.md                    # This file
tools/
  research_agent.py           # Main research tool
memory/
  api-usage/
    YYYY-MM-DD.json           # Daily logs
    spending.json             # Running totals
    reports/                  # Weekly summaries
```

## Security

- Credentials in `.env` (gitignored)
- API calls logged but never credentials
- Budget enforced at code level
- User can audit any query

---

*Budget: $10/month | Audit: Full logging enabled*
