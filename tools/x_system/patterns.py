from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .utils import utc_now_compact


TOPIC_MARKERS = {
    "seo": ["seo", "search traffic", "ranking", "organic"],
    "ppc": ["ppc", "google ads", "meta ads", "cpc", "roas"],
    "revops": ["revops", "sales ops", "pipeline", "crm", "forecast"],
    "sales_systems": ["outbound", "follow-up", "lead gen", "sales process", "prospecting"],
    "ai_ops": ["ai", "automation", "agent", "workflow"],
    "agency_performance": ["agency", "client", "retainer", "attribution", "reporting"],
}


@dataclass
class PatternResult:
    run_id: str
    summary: Dict[str, Any]
    artifact_path: Path


def _topic_from_text(text: str) -> str:
    body = text.lower()
    scores: Dict[str, int] = {k: 0 for k in TOPIC_MARKERS.keys()}
    for topic, markers in TOPIC_MARKERS.items():
        for m in markers:
            if m in body:
                scores[topic] += 1
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return top[0][0] if top and top[0][1] > 0 else "general_growth"


def _hook_type(text: str) -> str:
    body = text.strip().lower()
    if "?" in body:
        return "question_hook"
    if body.startswith("most ") or body.startswith("if your"):
        return "contrarian_claim"
    if body.startswith("how ") or "1/" in body:
        return "how_to"
    return "statement"


def _cta_style(text: str) -> str:
    body = text.lower()
    if "reply" in body or "comment" in body:
        return "explicit_reply_cta"
    if "what would" in body or "how would" in body:
        return "question_cta"
    return "none"


def _tone(text: str) -> str:
    body = text.lower()
    if "bullshit" in body or "nonsense" in body or "wrong" in body:
        return "blunt"
    if "should" in body or "must" in body:
        return "directive"
    return "practical"


def _controversy(text: str) -> float:
    body = text.lower()
    markers = ["wrong", "most", "nobody", "doesn't", "fails", "waste", "myth"]
    score = sum(1 for m in markers if m in body) / max(len(markers), 1)
    return round(min(1.0, score * 2.2), 2)


def extract_patterns(research_items: List[Dict[str, Any]], out_dir: Path, top_n: int = 40) -> PatternResult:
    run_id = utc_now_compact()
    top = research_items[:top_n]
    analyzed: List[Dict[str, Any]] = []
    topic_counts: Dict[str, int] = {}
    hook_counts: Dict[str, int] = {}
    cta_counts: Dict[str, int] = {}

    for item in top:
        text = item.get("text", "")
        topic = _topic_from_text(text)
        hook = _hook_type(text)
        cta = _cta_style(text)
        tone = _tone(text)
        controversy = _controversy(text)
        likely_discussion = float(item.get("metrics", {}).get("replies", 0)) >= 2
        row = {
            "tweet_id": item.get("tweet_id"),
            "topic": topic,
            "hook_type": hook,
            "cta_style": cta,
            "tone": tone,
            "controversy_score": controversy,
            "likely_icp_fit": item.get("scores", {}).get("icp_relevance", 0),
            "likely_discussion": likely_discussion,
            "composite_score": item.get("scores", {}).get("composite", 0),
        }
        analyzed.append(row)
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        hook_counts[hook] = hook_counts.get(hook, 0) + 1
        cta_counts[cta] = cta_counts.get(cta, 0) + 1

    summary = {
        "run_id": run_id,
        "top_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True),
        "top_hooks": sorted(hook_counts.items(), key=lambda x: x[1], reverse=True),
        "top_cta_styles": sorted(cta_counts.items(), key=lambda x: x[1], reverse=True),
        "items": analyzed,
    }
    artifact_path = out_dir / f"patterns_{run_id}.json"
    write_json_file(artifact_path, summary)
    return PatternResult(run_id=run_id, summary=summary, artifact_path=artifact_path)

