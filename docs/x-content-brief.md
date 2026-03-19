# X Content System Brief

Purpose: This document defines voice, themes, constraints, and scoring priorities for automated X posting. The goal is to attract operators, founders, and revenue leaders dealing with messy growth systems.

## 1) Inspiration Library

Source of truth lives in `tools/x_system_config/content/inspiration_library.json`.

Coverage includes: CRM hygiene, lead generation, attribution, sales handoff, tool overload, cold email, AI in marketing, founder marketing, growth strategy, SEO strategy, pipeline forecasting, founder expectations, growth consulting, AI agents, RevOps, dashboards, content marketing, cold outreach, sales enablement, product marketing, demand generation, AI writing, founder-led growth, cadence, agencies, sales cycles, founder content, data infrastructure, and strategy.

## 2) Voice Examples

Source of truth lives in `tools/x_system_config/content/voice_examples.json`.

Key style:
- operator-led point of view
- direct and clear language
- specific operational failure modes
- anti-hype, anti-generic, anti-corporate tone

## 3) Hard Constraints

Source of truth lives in `tools/x_system_config/content/hard_constraints.json`.

Core constraints:
- no emojis
- no hashtags
- no semicolons
- no em dash
- short mobile-readable paragraphs
- one idea per paragraph

## 4) CTA Preferences

Source of truth lives in `tools/x_system_config/content/cta_preferences.json`.

Primary goal: generate thoughtful operator replies.

Promotion rule: mention `allgreatthings.io` only when contextual and infrequent.

## 5) Scoring Priorities

Source of truth lives in `tools/x_system_config/content/score_weights.json`.

Priority order:
1. ICP relevance
2. Operator insight
3. Specificity
4. Reply potential
5. Authority signal

## 6) Contrarian Trigger Library

Purpose: These patterns are used to challenge assumptions, surface uncomfortable truths, and increase operator replies.

Each trigger includes a `pattern`, `description`, and `example`.

Source of truth lives in `tools/x_system_config/content/contrarian_triggers.json`.

How Gerald should use them:
- rotate patterns across runs
- avoid repeating the same pattern too frequently
- combine pattern + topic + operator truth

Example formula: `Pattern + Topic + Operator Truth`
