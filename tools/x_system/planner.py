from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .utils import utc_now_compact


@dataclass
class PlanResult:
    run_id: str
    opportunities: List[Dict[str, Any]]
    artifact_path: Path


def build_opportunities(
    pattern_summary: Dict[str, Any],
    out_dir: Path,
    primary_theme: str | None = None,
) -> PlanResult:
    run_id = utc_now_compact()
    topic_rank = [t[0] for t in pattern_summary.get("top_topics", [])]
    if not topic_rank:
        topic_rank = ["sales_systems", "revops", "agency_performance", "ai_ops"]

    if primary_theme:
        topic_rank = [primary_theme] + [t for t in topic_rank if t != primary_theme][:4]

    opportunities: List[Dict[str, Any]] = []
    default_pains = {
        "sales_systems": "Leads are generated but never consistently followed up.",
        "revops": "Leadership cannot trust pipeline or forecast numbers.",
        "agency_performance": "Marketing spend is disconnected from revenue outcomes.",
        "seo": "Traffic is up but qualified demand is flat.",
        "ppc": "Ad spend rises while close rate stalls.",
        "ai_ops": "Teams deploy AI tools without a reliable operating workflow.",
        "vibe_coding": "Shipping fast feels good until technical debt blocks the next feature.",
        "general_growth": "Growth feels random and non-repeatable.",
    }
    icp_segments = [
        "Founder/Owner",
        "CEO/President",
        "Head of Sales/RevOps",
        "Head of Marketing/Growth",
        "Operations Leader",
    ]
    limit = 1 if primary_theme else 5
    for idx, topic in enumerate(topic_rank[:limit]):
        opportunities.append(
            {
                "opportunity_id": f"{run_id}_{idx+1}",
                "topic": topic,
                "business_pain": default_pains.get(topic, default_pains["general_growth"]),
                "target_icp_segment": icp_segments[idx % len(icp_segments)],
                "reply_trigger": "Ask operators to share their current bottleneck or handoff failure.",
            }
        )

    artifact_path = out_dir / f"plan_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "opportunities": opportunities})
    return PlanResult(run_id=run_id, opportunities=opportunities, artifact_path=artifact_path)

