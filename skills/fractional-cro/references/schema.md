# Database Schema Reference

## Tables

### `leads`
Main table for tracking potential clients.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| source | TEXT | Where lead came from (upwork, linkedin, hackernews, etc.) |
| source_id | TEXT UNIQUE | Unique ID from source platform |
| company | TEXT | Company name |
| contact_name | TEXT | Person's name |
| title | TEXT | Job title |
| url | TEXT | Link to original posting/profile |
| description | TEXT | Full job description or bio |
| budget_signals | TEXT | Detected budget indicators |
| urgency_signals | TEXT | Detected urgency indicators |
| score | INTEGER | Calculated lead score (0-100) |
| status | TEXT | new, contacted, responded, meeting, closed, dead |
| tags | TEXT | Comma-separated tags |
| discovered_at | TIMESTAMP | When lead was found |
| contacted_at | TIMESTAMP | When first contact was made |
| notes | TEXT | Free-form notes |

### `interactions`
Tracks all outreach and responses.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| lead_id | INTEGER | Foreign key to leads.id |
| type | TEXT | email, linkedin_dm, call, meeting |
| content | TEXT | Full message content |
| sent_at | TIMESTAMP | When sent |
| response_received | BOOLEAN | Whether we got a reply |

### `api_costs`
Tracks API spending for cost monitoring.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| service | TEXT | Service name (openai, anthropic, etc.) |
| cost_usd | REAL | Cost in USD |
| usage_count | INTEGER | Number of API calls |
| recorded_at | TIMESTAMP | When recorded |

## Useful Queries

```sql
-- Top 10 unscored leads
SELECT * FROM leads WHERE score = 0 ORDER BY discovered_at DESC LIMIT 10;

-- Leads by source
SELECT source, COUNT(*) as count FROM leads GROUP BY source;

-- Conversion funnel
SELECT status, COUNT(*) as count FROM leads GROUP BY status;

-- High-value opportunities
SELECT * FROM leads WHERE score >= 80 AND status = 'new' ORDER BY score DESC;

-- Leads contacted this week
SELECT * FROM leads WHERE contacted_at >= date('now', '-7 days');
```
