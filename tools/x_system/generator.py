from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List

from .ai_helper import AIHelper
from .config import write_json_file
from .utils import utc_now_compact


@dataclass
class CandidateResult:
    run_id: str
    candidates: List[Dict[str, Any]]
    artifact_path: Path


def generate_candidates(
    opportunities: List[Dict[str, Any]],
    out_dir: Path,
    ai_helper: AIHelper,
    max_candidates: int = 10,
    min_total_score: int = 35,
    content_intel_enabled: bool = True,
    research_items: List[Dict[str, Any]] | None = None,
) -> CandidateResult:
    run_id = utc_now_compact()
    candidates: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    research_items = research_items or []

    for opp in opportunities:
        topic = str(opp.get("topic", "general_growth"))
        audience = str(opp.get("target_icp_segment", "Founder/Owner"))
        pain = str(opp.get("business_pain", "Growth and revenue operations are inconsistent."))
        insights = _build_insight_summary(topic, research_items)

        payload = None
        if content_intel_enabled:
            payload = ai_helper.generate_topic_posts(
                topic=topic,
                audience=audience,
                business_pain=pain,
                research_insights=insights,
                candidate_count=max_candidates,
            )
        if not payload:
            payload = _deterministic_fallback_payload(
                topic=topic,
                audience=audience,
                business_pain=pain,
                insight_summary=insights,
                count=max_candidates,
            )

        for row in payload.get("posts", []):
            text = str(row.get("text", "")).strip()
            scores = row.get("scores", {})
            total = int(scores.get("total", 0))
            fail_reason = _rejection_reason(text=text, total=total, min_total_score=min_total_score)
            candidate = {
                "candidate_id": f"{run_id}_{len(candidates)+len(rejected)+1}",
                "topic": topic,
                "intended_audience": audience,
                "business_pain": pain,
                "hook_type": "content_intel",
                "controversy_level": 0.7 if total >= 40 else 0.5,
                "predicted_reply_quality": 0.7 if "?" in text else 0.55,
                "why_fit": row.get("reasoning", opp.get("reply_trigger")),
                "text": text,
                "scores": scores,
                "reasoning": row.get("reasoning", ""),
            }
            if fail_reason:
                bad = dict(candidate)
                bad["rejected_reason"] = fail_reason
                rejected.append(bad)
            else:
                candidates.append(candidate)

    # Keep stable cap after filtering.
    candidates = candidates[:max_candidates]
    top_3_final = sorted(candidates, key=lambda c: int((c.get("scores") or {}).get("total", 0)), reverse=True)[:3]

    artifact_path = out_dir / f"candidates_{run_id}.json"
    write_json_file(
        artifact_path,
        {
            "run_id": run_id,
            "candidates": candidates,
            "rejected": rejected,
            "top_3_final": [
                {
                    "text": c.get("text", ""),
                    "why_it_should_work": c.get("reasoning", "") or c.get("why_fit", ""),
                }
                for c in top_3_final
            ],
        },
    )
    return CandidateResult(run_id=run_id, candidates=candidates, artifact_path=artifact_path)


BANNED_PHRASES = [
    "hot take",
    "most businesses",
    "most teams",
    "the real problem is",
    "the fix is",
    "game changer",
    "unlock",
    "leverage",
    "in today's world",
    "if your dashboard",
    "it's not x it's y",
    "thoughts?",
    "agree?",
    "what do you think?",
]

SPECIFIC_TERMS = [
    "lead response",
    "crm",
    "handoff",
    "attribution",
    "automation",
    "ppc",
    "funnel",
    "booked call",
    "close rate",
    "pipeline",
    "owner",
    "lead",
    "revenue leak",
]


def _word_count(text: str) -> int:
    return len([t for t in text.strip().split() if t])


def _contains_emoji(text: str) -> bool:
    # Broad emoji/symbol range guard.
    return bool(re.search(r"[\U0001F300-\U0001FAFF]", text))


def _rejection_reason(text: str, total: int, min_total_score: int) -> str:
    body = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in body:
            return f"contains banned phrase: {phrase}"
    if "#" in text:
        return "contains hashtag"
    if ";" in text:
        return "contains semicolon"
    if _contains_emoji(text):
        return "contains emoji"
    wc = _word_count(text)
    if wc < 35 or wc > 110:
        return f"word_count_out_of_range:{wc}"
    if not any(term in body for term in SPECIFIC_TERMS):
        return "missing_operational_specificity"
    if total < min_total_score:
        return f"score_below_threshold:{total}"
    return ""


def _build_insight_summary(topic: str, research_items: List[Dict[str, Any]]) -> str:
    focused = [i for i in research_items if str(i.get("scores", {}).get("topic", "")).lower() == topic.lower()]
    if not focused:
        focused = [i for i in research_items if topic.lower() in str(i.get("text", "")).lower()]
    if not focused:
        focused = research_items[:5]

    lines: List[str] = []
    for row in focused[:8]:
        metrics = row.get("metrics", {}) or {}
        text = str(row.get("text", "")).replace("\n", " ").strip()
        if len(text) > 220:
            text = text[:220].rstrip() + "..."
        lines.append(
            f"- {text} | replies={metrics.get('replies', 0)} likes={metrics.get('likes', 0)}"
        )
    return "\n".join(lines) if lines else "- No strong recent examples."


def _deterministic_fallback_payload(
    topic: str,
    audience: str,
    business_pain: str,
    insight_summary: str,
    count: int,
) -> Dict[str, Any]:
    scenario_bank = [
        "Leads from paid campaigns sit untouched for hours and nobody gets alerted.",
        "Marketing celebrates form fills while sales says half the leads are junk.",
        "Booked calls happen but no one owns the follow-up after the first meeting.",
        "Pipeline reports look clean but stage definitions change every week.",
        "The founder is still the routing layer for lead ownership decisions.",
        "Attribution dashboards claim wins that never show up in closed revenue.",
        "PPC spend climbs while close rate drops because handoff quality is weak.",
        "CRM fields are required but never audited, so forecasting is fiction.",
        "Automation exists but fails silently when ownership is not explicit.",
        "Content drives traffic but there is no operator accountable for conversion.",
    ]
    seed = {
        "hook_strength": 8,
        "specificity": 8,
        "authority": 8,
        "engagement_potential": 7,
        "icp_fit": 9,
    }
    posts: List[Dict[str, Any]] = []
    for idx in range(count):
        scenario = scenario_bank[idx % len(scenario_bank)]
        text = (
            f"A surprising number of {audience} teams hit the same wall.\n\n"
            f"{scenario}\n\n"
            f"That is why {business_pain.lower()}\n\n"
            "Where does ownership break first in your process?"
        )
        total = sum(seed.values()) - (idx % 3)
        scores = dict(seed)
        scores["total"] = total
        posts.append(
            {
                "text": text,
                "scores": scores,
                "reasoning": f"Operational failure mode tied to topic {topic}. Insights sampled: {insight_summary[:120]}",
            }
        )
    top_3 = [
        {
            "text": p["text"],
            "why_it_should_work": p["reasoning"],
        }
        for p in posts[:3]
    ]
    return {"topic": topic, "posts": posts, "top_3_final": top_3}

