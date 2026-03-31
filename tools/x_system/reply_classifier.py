from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .ai_helper import AIHelper
from .config import write_json_file
from .utils import utc_now_compact


HIGH_INTENT_MARKERS = [
    "how would you fix",
    "we struggle",
    "what tools",
    "can you help",
    "exactly our problem",
    "how did you do this",
    "need help",
]

LOW_SIGNAL_MARKERS = ["great post", "nice post", "🔥", "👏", "lol", "gm"]
TROLL_MARKERS = ["scam", "idiot", "stupid", "trash"]


@dataclass
class ClassificationResult:
    run_id: str
    items: List[Dict[str, Any]]
    artifact_path: Path


def classify_replies(
    replies: List[Dict[str, Any]],
    out_dir: Path,
    ai_helper: AIHelper,
) -> ClassificationResult:
    run_id = utc_now_compact()
    items: List[Dict[str, Any]] = []

    for reply in replies:
        text = (reply.get("text") or "").strip()
        body = text.lower()
        label = "public_reply_only"
        reason = "default_public_reply"

        if not text or len(text) < 3:
            label = "ignore"
            reason = "empty_or_too_short"
        elif any(marker in body for marker in TROLL_MARKERS):
            label = "ignore"
            reason = "hostile_or_troll_signal"
        elif any(marker in body for marker in LOW_SIGNAL_MARKERS):
            label = "ignore"
            reason = "low_signal_filler"
        elif any(marker in body for marker in HIGH_INTENT_MARKERS):
            label = "public_reply_dm"
            reason = "high_intent_signal"
        elif "?" in body:
            label = "public_reply_only"
            reason = "question_signal"

        ai_hint = ai_helper.classify_reply_hint(text)
        if ai_hint in {"ignore", "public_reply_only", "public_reply_dm", "human_review"}:
            label = ai_hint
            reason = f"ai_hint_{ai_hint}"

        items.append(
            {
                "reply_id": reply.get("id"),
                "author_id": reply.get("author_id"),
                "text": text,
                "classification": label,
                "reason": reason,
            }
        )

    artifact_path = out_dir / f"classification_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "items": items})
    return ClassificationResult(run_id=run_id, items=items, artifact_path=artifact_path)

