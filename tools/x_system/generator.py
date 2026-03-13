from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .ai_helper import AIHelper
from .config import write_json_file
from .templates import operator_templates
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
    max_candidates: int = 5,
) -> CandidateResult:
    run_id = utc_now_compact()
    candidates: List[Dict[str, Any]] = []
    for opp in opportunities:
        templates = operator_templates(opp)
        for hook_type, base_text in templates.items():
            final_text = ai_helper.improve_post(base_text, {"topic": opp.get("topic", "")}) or base_text
            candidates.append(
                {
                    "candidate_id": f"{run_id}_{len(candidates)+1}",
                    "topic": opp.get("topic"),
                    "intended_audience": opp.get("target_icp_segment"),
                    "business_pain": opp.get("business_pain"),
                    "hook_type": hook_type,
                    "controversy_level": 0.7 if hook_type in ("strong_opinion", "contrarian") else 0.4,
                    "predicted_reply_quality": 0.7 if "?" in final_text else 0.5,
                    "why_fit": opp.get("reply_trigger"),
                    "text": final_text,
                }
            )
            if len(candidates) >= max_candidates:
                break
        if len(candidates) >= max_candidates:
            break

    artifact_path = out_dir / f"candidates_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "candidates": candidates})
    return CandidateResult(run_id=run_id, candidates=candidates, artifact_path=artifact_path)

