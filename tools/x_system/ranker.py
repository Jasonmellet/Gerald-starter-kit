from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .utils import utc_now_compact


@dataclass
class RankingResult:
    run_id: str
    ranked: List[Dict[str, Any]]
    winner: Dict[str, Any]
    artifact_path: Path


def rank_candidates(
    candidates: List[Dict[str, Any]],
    out_dir: Path,
    scoring_weights: Dict[str, float],
    min_total_score: int = 35,
) -> RankingResult:
    run_id = utc_now_compact()
    ranked: List[Dict[str, Any]] = []
    for c in candidates:
        scorecard = c.get("scores") or {}
        if isinstance(scorecard, dict) and scorecard:
            # New content-intel path: use explicit rubric scores (1-10, total up to 50).
            hs = float(scorecard.get("hook_strength", 0))
            sp = float(scorecard.get("specificity", 0))
            au = float(scorecard.get("authority", 0))
            ep = float(scorecard.get("engagement_potential", 0))
            icp = float(scorecard.get("icp_fit", 0))
            total_50 = float(scorecard.get("total", hs + sp + au + ep + icp))
            if total_50 < float(min_total_score):
                continue
            total = total_50 / 50.0
        else:
            # Legacy fallback scoring path.
            icp_score = 0.9 if "Founder" in (c.get("intended_audience") or "") else 0.75
            opinion_score = float(c.get("controversy_level", 0.5))
            clarity_score = 0.85 if len((c.get("text") or "").strip()) <= 280 else 0.65
            reply_quality = float(c.get("predicted_reply_quality", 0.5))
            pain_score = 0.8 if c.get("business_pain") else 0.5
            total = (
                icp_score * scoring_weights.get("icp_match", 0.35)
                + opinion_score * scoring_weights.get("opinion_strength", 0.2)
                + clarity_score * scoring_weights.get("clarity", 0.15)
                + pain_score * scoring_weights.get("pain_relevance", 0.15)
                + reply_quality * scoring_weights.get("reply_likelihood", 0.15)
            )
        row = dict(c)
        row["rank_score"] = round(total, 4)
        ranked.append(row)

    ranked.sort(key=lambda r: float(r.get("rank_score", 0.0)), reverse=True)
    winner = ranked[0] if ranked else {}
    artifact_path = out_dir / f"ranked_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "ranked": ranked, "winner": winner})
    return RankingResult(run_id=run_id, ranked=ranked, winner=winner, artifact_path=artifact_path)

