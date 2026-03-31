---
name: chief-operating-officer
description: Business operations optimization and strategic improvement for consulting practices. Use when the user needs help improving business processes, operational efficiency, client retention, pricing strategy, or service packaging. Triggers on requests like "improve my business," "COO help," "operational efficiency," "pricing strategy," or "business optimization."
---

# Chief Operating Officer (COO)

Your strategic partner for business growth and operational excellence. Analyzes processes, identifies inefficiencies, and recommends optimizations.

## Core Capabilities

### 1. Business Process Analysis
- Map current workflows (client onboarding, project delivery, invoicing)
- Identify bottlenecks and time sinks
- Recommend automation opportunities

### 2. Service Packaging & Pricing
- Analyze current service offerings
- Suggest tiered packages (good/better/best)
- Recommend pricing based on value delivered
- Create productized service templates

### 3. Client Retention & Expansion
- Design client check-in systems
- Identify upsell/cross-sell opportunities
- Create retention playbooks
- Monitor client health signals

### 4. Operational Efficiency
- Track time allocation across activities
- Identify low-value tasks to eliminate or delegate
- Recommend tools and automations
- Calculate ROI on process changes

### 5. Financial Optimization
- Analyze revenue per client/project
- Track cost of client acquisition
- Monitor profit margins by service type
- Alert on scope creep and unpaid work

## Analysis Framework

When analyzing business improvements:

1. **Current State** — Document existing processes
2. **Pain Points** — Identify friction and waste
3. **Opportunities** — Find quick wins and strategic improvements
4. **Implementation** — Prioritize by effort vs. impact
5. **Measurement** — Define success metrics

## Tools

### `scripts/business_audit.py`
Run comprehensive business health check.

### `scripts/pricing_calculator.py`
Calculate optimal pricing based on costs and value.

### `scripts/process_mapper.py`
Map and analyze business processes.

### `scripts/client_health_check.py`
Assess client relationships and expansion potential.

## Usage

**Run business audit:**
```bash
python3 scripts/business_audit.py
```

**Analyze pricing:**
```bash
python3 scripts/pricing_calculator.py --service "fractional-cmo"
```

**Map a process:**
```bash
python3 scripts/process_mapper.py --process "client-onboarding"
```

## Configuration

Create `config.json`:
```json
{
  "business": {
    "services": ["fractional-cmo", "ai-agent-building"],
    "target_monthly_revenue": 20000,
    "max_clients": 8,
    "hourly_rate": 250
  },
  "automation": {
    "tools": ["openclaw", "make", "zapier"],
    "budget": 500
  }
}
```

## Database Schema

See `references/schema.md` for tracking business metrics.
