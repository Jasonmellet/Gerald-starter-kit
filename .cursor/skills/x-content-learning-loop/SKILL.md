---
name: x-content-learning-loop
description: Run weekly X content performance reviews and convert findings into concrete config updates for topics, triggers, score weights, CTA choices, and voice examples. Use when the user asks what performed, how to improve next week, or how to tune X content strategy with evidence.
---

# X Content Learning Loop

## Use when

- User asks for weekly content review
- User asks what to change based on top/weak post performance
- User requests tuning of X strategy and generation configuration

## Required reads

- `docs/x-weekly-content-review.md`
- `docs/x-content-brief.md`
- `docs/x-icp-definition.md`

## Config targets

- `tools/x_system_config/content/contrarian_triggers.json`
- `tools/x_system_config/content/score_weights.json`
- `tools/x_system_config/content/cta_preferences.json`
- `tools/x_system_config/content/voice_examples.json`

## Weekly process

1. Collect evidence
   - Compile top posts and weak posts for the week
   - Include replies, likes, reposts, profile visits, DMs, and leads where available
2. Analyze patterns
   - What topics and trigger patterns performed
   - What underperformed and why
   - Which CTA type produced stronger conversation quality
3. Map to ICP
   - Keep only adjustments that improve founder/RevOps/growth-operator relevance
4. Propose concrete config changes
   - Specific entries to add, reduce, or reweight
5. Apply updates (when requested)
   - Edit target JSON files with minimal, testable changes

## Output format

```markdown
# Weekly X Content Review

- Week of: <date>
- Posts reviewed: <n>
- Top performers analyzed: <n>
- Underperformers analyzed: <n>

## What worked
- <pattern + evidence>

## What underperformed
- <pattern + evidence>

## Recommended config updates
- `contrarian_triggers.json`: <change>
- `score_weights.json`: <change>
- `cta_preferences.json`: <change>
- `voice_examples.json`: <change>

## Next week experiment plan
- <3-5 specific experiments>
```

## Guardrails

- Avoid vague advice; tie every recommendation to observed evidence.
- Keep edits incremental so weekly effects are attributable.
