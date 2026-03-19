## Gerald

Gerald is an AI-assisted opportunity discovery and outreach copilot for a consulting / fractional CMO / AI agent business.

It focuses on:

- **Discovering prospects on X** based on buying and pain signals.
- **Detecting and structuring signals** from profiles and posts.
- **Enriching and scoring opportunities** with explicit, transparent criteria.
- **Drafting personalized outreach** (DM, reply, email-style) grounded in evidence.
- **Queuing everything for review** – no automatic sending by default.

### Setup

- **Python**: 3.11 or newer.
- From the `gerald` directory:

```bash
pip install -e .
```

- Copy `.env.example` to `.env` and fill in:
  - X credentials (`X_BEARER_TOKEN` or others as needed).
  - Anthropic keys and model names.
  - Optional overrides for lookback days and limits.

### Database

Gerald uses SQLite by default (`sqlite:///./gerald.db`).

Create the schema once:

```bash
python -m app.cli.main init-db
```

If you have an existing database from before ICP fields were added, add the new Prospect columns with:

```bash
sqlite3 gerald.db "ALTER TABLE prospects ADD COLUMN icp_score REAL; ALTER TABLE prospects ADD COLUMN prospect_status VARCHAR(32); ALTER TABLE prospects ADD COLUMN discovery_reason TEXT;"
```

If you have an existing database from before review and contact-history were added, create the new table and column (SQLite does not support adding a column with a default easily; you may need to recreate the opportunities table or add the column and backfill):

- `contact_history` is created automatically by `init-db` (run `python -m app.cli.main init-db` again to create the table if you use `create_all`).
- For `opportunities.review_status`, add the column and set defaults:  
  `sqlite3 gerald.db "ALTER TABLE opportunities ADD COLUMN review_status VARCHAR(32) DEFAULT 'pending';"`  
  (If your SQLite version does not support ADD COLUMN with DEFAULT, add the column and update existing rows to `'pending'`.)

(New installs get all tables and columns automatically from `init-db`.)

### Core commands

All commands are run from the `gerald` directory:

- **Discovery** – find prospects from X:

```bash
python -m app.cli.main discover
```

- **Analyze** – extract signals and enrich prospects:

```bash
python -m app.cli.main analyze
```

- **Score** – score prospects and create/update opportunities:

```bash
python -m app.cli.main score
```

- **Draft** – generate outreach drafts for top opportunities:

```bash
python -m app.cli.main draft
```

- **Digest** – print a digest and write `outputs/daily_digest.md`:

```bash
python -m app.cli.main digest
```

- **Review queue**:

```bash
python -m app.cli.main review list
python -m app.cli.main review approve <opportunity_id>
python -m app.cli.main review reject <opportunity_id>
python -m app.cli.main review edit <opportunity_id>
python -m app.cli.main review archive <opportunity_id>
```

- **Full pipeline**:

```bash
python -m app.cli.main run-pipeline
```

- **Run autonomous** – one command: create run, discover (100 candidates), analyze, score, draft, select top 5, **send DMs** (or dry-run), write run + outreach reports. Uses `DAILY_DISCOVERY_LIMIT` (default 100) and `DAILY_OUTREACH_LIMIT` (default 5). Send behavior follows `OUTREACH_SEND_MODE` and `ALLOW_LIVE_SEND`:

```bash
python3 -m app.cli.main run-autonomous
# or from repo root: ./run run-autonomous
```

- **Automation (run without opening a terminal)** – Gerald doesn’t have a built-in daemon. To run the full pipeline on a schedule (e.g. daily), use **cron** or **launchd** and point them at the script:

```bash
# Example: run daily at 9:00 AM, log to outputs/cron.log
0 9 * * * /path/to/gerald/scripts/run-autonomous-daily.sh >> /path/to/gerald/outputs/cron.log 2>&1
```

Edit `scripts/run-autonomous-daily.sh` so the path matches your machine. Ensure `.env` is in the `gerald` directory so the script picks up your keys and send-mode settings.

### Architecture overview

- `app/config.py` – Pydantic settings, env handling, and defaults.
- `app/logging.py` – shared logging configuration.
- `app/db.py` – SQLAlchemy engine, session management, and `create_all`.
- `app/models.py` – ORM models (`Prospect`, `Post`, `Signal`, `Opportunity`, `Draft`, `Interaction`).
- `app/schemas.py` – Pydantic schemas for structured model IO and scores.
- `app/constants.py` – signal taxonomy, opportunity statuses, channels, interaction types.
- `app/clients/` – X client (`x_client.py`) and Anthropic client (`anthropic_client.py`).
- `app/prompts/` – prompt templates kept separate from logic.
- `app/repositories/` – database access and dedupe logic.
- `app/services/` – discovery, signals, enrichment, scoring, drafting, review, digest orchestration.
- `app/cli/main.py` – Typer-based CLI entrypoint.

### Search queries and model routing

- Discovery queries are configured via `Settings.discovery_queries` in `config.py` and can be overridden via env if desired.
- Anthropic model names are configured in `.env` with:
  - `ANTHROPIC_CHEAP_MODEL`
  - `ANTHROPIC_STRONG_MODEL`

The services route work to the **cheap** model for:

- First-pass signal extraction, light formatting, and cleanup.

And to the **strong** model for:

- Prospect summaries, scoring rationale, outreach angle generation, draft generation, and digest synthesis.

If you add a **Kimi (Moonshot)** or other LLM backend to Gerald, follow the workspace prompting and usage guidance so prompts stay consistent: see **`KIMI-GUIDANCE.md`** in the repo root (clear instructions, roles, delimiters, steps, vision, web search, token/cost awareness).

### Discovery filtering and ICP

Gerald prioritizes **founder-led companies** and **B2B opportunities** that might realistically hire fractional CMO / GTM / AI automation help.

- **Targeted queries** – Default discovery queries are tuned for founder/GTM signals (e.g. "hiring first marketer", "need help with growth", "seed round", "b2b saas", "building in public", "ai startup"). You can override them via `Settings.discovery_queries` in config or env.

- **Negative filters** – During discovery, accounts are skipped (not saved) if:
  - Follower count is below 20, or
  - There is no bio and no website, or
  - The bio contains negative keywords (e.g. musician, artist, streamer, content creator, affiliate, giveaway, fan account, gamer). These reduce junk from creators, influencers, and non-business accounts.

- **ICP scoring** – A heuristic score is computed from the profile: founder/startup/B2B keywords in the bio (+3 / +2), website present (+2) or absent (-1), followers > 200 (+1), negative keywords in bio (-3). Only prospects with **ICP score >= 2** are saved and sent to the analyze stage (signals + enrichment). This reduces expensive LLM analysis on obviously irrelevant accounts.

- **Opportunity threshold** – After scoring, prospects with **overall_score < 50** do not get an Opportunity record and are marked `prospect_status = "low_priority"`. The daily digest and draft pipeline only include opportunities that meet this threshold.

- **Brand-account filter** – Accounts whose bio or handle suggests a company/brand account (e.g. "official account", "brand account") are skipped so discovery prefers individuals.

### Outreach Safety and Review

Gerald is designed as a **signal-detection and outreach assistant**, not a spam automation tool. All outreach requires human review and approval before any message is sent.

- **Outreach qualification** – Only opportunities that pass stricter criteria receive auto-generated DM drafts:
  - **overall_score >= 65**, **buyer_score >= 60**, **confidence_score >= 50**
  - Others still appear in the digest and review list but do not get drafts until you choose to draft them manually or relax the gate.

- **Manual review workflow** – Use the review queue before treating an opportunity as ready to contact:
  - `review list` – list top opportunities with review status
  - `review approve <opportunity_id>` – mark as approved (eligible for outreach when sending is implemented)
  - `review reject <opportunity_id>` – mark as rejected
  - `review edit <opportunity_id>` – open the DM draft in `$EDITOR` and save changes
  - `review archive <opportunity_id>` – archive the opportunity

- **Duplicate contact protection** – The system does not generate new drafts for prospects who have been contacted in the last **30 days** (recorded in `contact_history`). When sending is implemented, outbound messages will be logged there to avoid double-messaging.

- **Tiered opportunity ranking** – The digest labels opportunities as **Tier 1** (score ≥ 70), **Tier 2** (60–70), or **Tier 3** (50–60). Initial outreach should focus on Tier 1; lower tiers are visible for context or later follow-up.

### Tests

Run tests from the `gerald` directory:

```bash
pytest
```

Tests currently cover scoring formulas, basic parsing of structured model output, and drafting output structure.

### Current limitations and future sending

- Gerald does **not** send DMs or emails. All drafts go into a review queue and require human approval.
- X API usage is read-only in this MVP.
- Anthropic prompts use JSON patterns but still depend on model behavior; defensive parsing is in place.

In the future, a sending workflow would plug into:

- `review_service` (after approval), plus a dedicated send service that:
  - Uses X or email APIs to send approved drafts.
  - Logs `Interaction` rows with outcomes.
  - Remains behind explicit config toggles and confirmation steps.

