# X Weekly Content Review

Purpose: Build a weekly evidence base of what content performs, then feed those lessons back into Gerald.

Cadence: Every week (suggest Sunday evening or Monday morning).

## Automated pull (API)

From the repo root, fetch everything the account posted in the last N days (posts, replies, RTs), with `public_metrics`:

```bash
python3 tools/x_posts_window_report.py --days 7
```

- **Requires:** `X_BEARER_TOKEN` in `.env`, plus either `X_ACCOUNT_USERNAME`, or `X_ACCESS_TOKEN` in the form `<user_id>-...` (same as other X tools).
- **Writes (under `outputs/`, gitignored):**
  - `x_posts_last_7d_<timestamp>.json` — full API payload for spreadsheets or scripts
  - `x_posts_last_7d_<timestamp>.md` — short Markdown summary: counts by type, pipeline-template hits, top 5 by likes (all vs originals-only)
- **Options:** `--username HANDLE`, `--days 14`, `--no-md`, `--json-out PATH`, `--md-out PATH`

Use the `.md` file as the quantitative half of the week; then fill in the qualitative sections below (why it worked, what to change). For turning learnings into config edits, follow `.cursor/skills/x-content-learning-loop/SKILL.md`.

**Positioning alignment:** Re-read `BUSINESS-MEMORY.md` (ICP + win themes) before writing “pattern learnings” so X tweaks match who you’re trying to attract.

## Week Of: YYYY-MM-DD

### 1) Top Posts (up to 10)

For each post, capture:
- post_id
- post_url
- topic
- contrarian_pattern_used
- post_text
- metrics: replies / likes / reposts / profile_visits / DMs / leads
- why_it_worked (1-3 bullets)

Template row:
- post_id:
- post_url:
- topic:
- contrarian_pattern_used:
- post_text:
- metrics:
  - replies:
  - likes:
  - reposts:
  - profile_visits:
  - dms:
  - leads:
- why_it_worked:
  - 

### 2) Weak Posts (up to 10)

For each post, capture:
- post_id
- post_url
- topic
- contrarian_pattern_used
- post_text
- metrics: replies / likes / reposts / profile_visits / DMs / leads
- why_it_underperformed (1-3 bullets)

Template row:
- post_id:
- post_url:
- topic:
- contrarian_pattern_used:
- post_text:
- metrics:
  - replies:
  - likes:
  - reposts:
  - profile_visits:
  - dms:
  - leads:
- why_it_underperformed:
  - 

### 3) Pattern Learnings

- Patterns that performed well this week:
  - 
- Patterns to reduce next week:
  - 
- Topics that performed well:
  - 
- Topics to reduce:
  - 
- Best CTA type this week:
  - 

### 4) Next Week Adjustments

Make concrete updates in:
- `tools/x_system_config/content/contrarian_triggers.json`
- `tools/x_system_config/content/score_weights.json`
- `tools/x_system_config/content/cta_preferences.json`
- `tools/x_system_config/content/voice_examples.json`

Planned changes:
- 
