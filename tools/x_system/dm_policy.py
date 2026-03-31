from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DmDecision:
    allow_dm: bool
    reason: str


def evaluate_dm_policy(classification_item: Dict[str, str], icp_threshold: float = 0.4) -> DmDecision:
    # Current v1 policy: only allow DM for public_reply_dm classification.
    # We keep signature extensible for future ICP scoring inputs.
    label = classification_item.get("classification", "")
    if label == "public_reply_dm":
        return DmDecision(True, "classification_high_intent")
    if label == "human_review":
        return DmDecision(False, "needs_human_review")
    return DmDecision(False, "not_high_intent")

