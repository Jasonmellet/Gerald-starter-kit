from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Set

from .ai_helper import AIHelper
from .config import write_json_file
from .utils import utc_now_compact


@dataclass
class CandidateResult:
    run_id: str
    candidates: List[Dict[str, Any]]
    artifact_path: Path
    telemetry: Dict[str, Any]
    degraded: bool


def generate_candidates(
    opportunities: List[Dict[str, Any]],
    out_dir: Path,
    ai_helper: AIHelper,
    max_candidates: int = 10,
    min_total_score: int = 35,
    min_opener_uniqueness: float = 0.6,
    content_intel_enabled: bool = True,
    degraded_mode_skip_publish: bool = True,
    research_items: List[Dict[str, Any]] | None = None,
    content_context: Dict[str, Any] | None = None,
) -> CandidateResult:
    run_id = utc_now_compact()
    candidates: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    generation_telemetry: List[Dict[str, Any]] = []
    research_items = research_items or []
    content_context = content_context or {}

    for opp in opportunities:
        topic = str(opp.get("topic", "general_growth"))
        audience = str(opp.get("target_icp_segment", "Founder/Owner"))
        pain = str(opp.get("business_pain", "Growth and revenue operations are inconsistent."))
        insights = _build_insight_summary(topic, research_items)
        context_snippet = _content_context_snippet(content_context, topic=topic)
        if context_snippet:
            insights = f"{insights}\n\nExternal context:\n{context_snippet}"

        payload = None
        source = "fallback"
        topic_telemetry: Dict[str, Any] = {
            "topic": topic,
            "llm_used": False,
            "fallback_used": True,
            "fallback_reason": "content_intel_disabled",
            "model": "",
            "api_status": "disabled",
        }
        if content_intel_enabled:
            llm_result = ai_helper.generate_topic_posts_with_meta(
                topic=topic,
                audience=audience,
                business_pain=pain,
                research_insights=insights,
                candidate_count=max_candidates,
            )
            payload = llm_result.get("payload")
            topic_telemetry.update(llm_result.get("telemetry") or {})
            source = "llm" if payload else "fallback"

        if not payload:
            payload = _deterministic_fallback_payload(
                topic=topic,
                audience=audience,
                business_pain=pain,
                insight_summary=insights,
                count=max_candidates,
            )
            topic_telemetry["fallback_used"] = True
            topic_telemetry["fallback_reason"] = topic_telemetry.get("fallback_reason") or "llm_payload_missing"

        seen_openers: Set[str] = set()
        accepted_for_topic = 0

        for row in payload.get("posts", []):
            text = str(row.get("text", "")).strip()
            scores = row.get("scores", {})
            total = int(scores.get("total", 0))
            fail_reason = _rejection_reason(text=text, total=total, min_total_score=min_total_score)
            opener = _opener_key(text)
            if not fail_reason and opener in seen_openers:
                fail_reason = "duplicate_opener"
            if not fail_reason:
                seen_openers.add(opener)
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
                "generation_source": source,
            }
            if fail_reason:
                bad = dict(candidate)
                bad["rejected_reason"] = fail_reason
                rejected.append(bad)
            else:
                candidates.append(candidate)
                accepted_for_topic += 1

        topic_telemetry["accepted_candidates"] = accepted_for_topic
        topic_telemetry["rejected_candidates"] = max(0, max_candidates - accepted_for_topic)
        generation_telemetry.append(topic_telemetry)

    # Keep stable cap after filtering.
    candidates = candidates[:max_candidates]
    opener_ratio = _opener_uniqueness_ratio(candidates)
    lexical_variance = _lexical_variance(candidates)
    degraded = False
    degraded_reason = ""
    if not candidates:
        degraded = True
        degraded_reason = "no_candidates_after_filters"
    elif opener_ratio < min_opener_uniqueness or lexical_variance < 0.35:
        degraded = True
        degraded_reason = f"low_diversity(opener_ratio={opener_ratio:.2f},lexical_variance={lexical_variance:.2f})"
        if degraded_mode_skip_publish:
            for c in candidates:
                bad = dict(c)
                bad["rejected_reason"] = degraded_reason
                rejected.append(bad)
            candidates = []

    top_3_final = sorted(candidates, key=lambda c: int((c.get("scores") or {}).get("total", 0)), reverse=True)[:3]
    telemetry = {
        "generation": generation_telemetry,
        "content_context_summary": {
            "inspiration_count": len(content_context.get("inspiration_library") or []),
            "voice_examples_count": len(content_context.get("voice_examples") or []),
            "contrarian_trigger_count": len(content_context.get("contrarian_triggers") or []),
            "has_icp_definition": bool(content_context.get("icp_definition")),
            "has_constraints": bool(content_context.get("hard_constraints")),
            "has_cta_preferences": bool(content_context.get("cta_preferences")),
        },
        "diversity": {
            "opener_uniqueness_ratio": round(opener_ratio, 4),
            "lexical_variance": round(lexical_variance, 4),
            "min_opener_uniqueness": float(min_opener_uniqueness),
            "degraded": degraded,
            "degraded_reason": degraded_reason,
            "degraded_mode_skip_publish": bool(degraded_mode_skip_publish),
        },
    }

    artifact_path = out_dir / f"candidates_{run_id}.json"
    write_json_file(
        artifact_path,
        {
            "run_id": run_id,
            "candidates": candidates,
            "rejected": rejected,
            "telemetry": telemetry,
            "top_3_final": [
                {
                    "text": c.get("text", ""),
                    "why_it_should_work": c.get("reasoning", "") or c.get("why_fit", ""),
                }
                for c in top_3_final
            ],
        },
    )
    return CandidateResult(
        run_id=run_id,
        candidates=candidates,
        artifact_path=artifact_path,
        telemetry=telemetry,
        degraded=degraded,
    )


def _content_context_snippet(content_context: Dict[str, Any], topic: str) -> str:
    inspiration = content_context.get("inspiration_library") or []
    voice = content_context.get("voice_examples") or []
    triggers = content_context.get("contrarian_triggers") or []
    icp = content_context.get("icp_definition") or {}
    constraints = content_context.get("hard_constraints") or {}
    snippets: List[str] = []

    focused = []
    for row in inspiration:
        if not isinstance(row, dict):
            continue
        if str(row.get("topic", "")).lower() == topic.lower() or not row.get("topic"):
            focused.append(row)
    for row in focused[:6]:
        fm = str(row.get("failure_mode", "")).strip()
        bc = str(row.get("business_consequence", "")).strip()
        ot = str(row.get("operator_truth", "")).strip()
        line = " | ".join([part for part in [fm, bc, ot] if part])
        if line:
            snippets.append(f"- {line}")

    for row in (voice[:3] if isinstance(voice, list) else []):
        if not isinstance(row, dict):
            continue
        txt = str(row.get("text", "")).replace("\n", " ").strip()
        if txt:
            snippets.append(f"- voice_example: {txt[:180]}")

    for row in (triggers[:3] if isinstance(triggers, list) else []):
        if not isinstance(row, dict):
            continue
        pattern = str(row.get("pattern", "")).strip()
        desc = str(row.get("description", "")).strip()
        if pattern:
            snippets.append(f"- contrarian_pattern: {pattern} | {desc[:120]}")

    if isinstance(icp, dict):
        primary = icp.get("primary_icp") or {}
        role = str(primary.get("role", "")).strip()
        company = str(primary.get("company_profile", "")).strip()
        if role or company:
            snippets.append(f"- primary_icp: {role} | {company}")

    fp = constraints.get("forbidden_phrases") if isinstance(constraints, dict) else []
    if isinstance(fp, list) and fp:
        snippets.append("- forbidden_phrases: " + ", ".join(str(x) for x in fp[:20]))
    return "\n".join(snippets[:12])


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


def _opener_key(text: str) -> str:
    first = (text.splitlines()[0] if text else "").strip().lower()
    return " ".join(first.split())


def _opener_uniqueness_ratio(candidates: List[Dict[str, Any]]) -> float:
    if not candidates:
        return 0.0
    unique = {_opener_key(str(c.get("text", ""))) for c in candidates}
    return len(unique) / float(len(candidates))


def _tokenize_for_variance(text: str) -> Set[str]:
    body = re.sub(r"[^a-z0-9\\s]", " ", text.lower())
    return {t for t in body.split() if len(t) >= 4}


def _lexical_variance(candidates: List[Dict[str, Any]]) -> float:
    if len(candidates) < 2:
        return 0.0
    sets = [_tokenize_for_variance(str(c.get("text", ""))) for c in candidates]
    overlaps: List[float] = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a, b = sets[i], sets[j]
            if not a or not b:
                continue
            inter = len(a.intersection(b))
            union = len(a.union(b))
            if union == 0:
                continue
            overlaps.append(inter / float(union))
    if not overlaps:
        return 0.0
    avg_overlap = sum(overlaps) / float(len(overlaps))
    return max(0.0, 1.0 - avg_overlap)


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
    opener_bank = [
        "A surprising number of SMB founders learn this too late.",
        "You can spot process debt in 5 minutes once this shows up.",
        "The leak in a lot of funnels is hiding in plain sight.",
        "A lot of growth stalls start with one ownership gap.",
        "This is where solid teams quietly lose revenue each week.",
        "Most missed targets start with this handoff failure.",
        "The pipeline problem usually starts earlier than leaders think.",
        "This pattern shows up in almost every messy CRM I audit.",
        "Operators feel this issue before dashboards ever show it.",
        "Revenue teams keep reliving this avoidable mistake.",
    ]
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
        opener = opener_bank[idx % len(opener_bank)]
        scenario = scenario_bank[idx % len(scenario_bank)]
        text = (
            f"{opener}\n\n"
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

