from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .dm_policy import evaluate_dm_policy
from .state_manager import StateManager
from .utils import utc_now_compact
from .x_client import XClient


@dataclass
class DmActionResult:
    run_id: str
    actions: List[Dict[str, Any]]
    artifact_path: Path


def _build_dm_text(reply_text: str) -> str:
    body = reply_text.lower()
    if "seo" in body or "ppc" in body:
        return "Thanks for jumping in on that thread. If useful, I can share a simple way to tie SEO/PPC effort back to pipeline outcomes."
    if "crm" in body or "pipeline" in body:
        return "Appreciate your comment. If it helps, I can share the exact CRM/pipeline structure we use to reduce handoff leakage."
    return "Thanks for engaging on that post. If useful, I can share a practical framework we use to turn this into a repeatable workflow."


def handle_dms(
    x_client: XClient,
    classified_items: List[Dict[str, Any]],
    state: StateManager,
    campaign_id: str,
    out_dir: Path,
    dry_run: bool,
) -> DmActionResult:
    run_id = utc_now_compact()
    actions: List[Dict[str, Any]] = []

    for item in classified_items:
        user_id = str(item.get("author_id") or "")
        reply_id = str(item.get("reply_id") or "")
        if not user_id or not reply_id:
            continue

        decision = evaluate_dm_policy(item)
        if not decision.allow_dm:
            actions.append({"reply_id": reply_id, "user_id": user_id, "action": "skip_dm", "reason": decision.reason})
            continue

        if state.was_dm_sent(campaign_id, user_id):
            actions.append(
                {
                    "reply_id": reply_id,
                    "user_id": user_id,
                    "action": "skip_dm_duplicate",
                    "reason": "already_sent_for_campaign",
                }
            )
            continue

        dm_text = _build_dm_text(item.get("text", ""))
        if dry_run:
            dm_event_id = f"dryrun_dm_{reply_id}"
            action = {
                "reply_id": reply_id,
                "user_id": user_id,
                "action": "dry_run_dm",
                "reason": decision.reason,
                "dm_text": dm_text,
                "dm_event_id": dm_event_id,
            }
        else:
            payload = x_client.send_dm(user_id, dm_text)
            dm_event_id = payload.get("data", {}).get("dm_event_id")
            action = {
                "reply_id": reply_id,
                "user_id": user_id,
                "action": "sent_dm",
                "reason": decision.reason,
                "dm_text": dm_text,
                "dm_event_id": dm_event_id,
            }

        state.mark_dm_sent(campaign_id, user_id, action)
        actions.append(action)

    artifact_path = out_dir / f"dm_actions_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "campaign_id": campaign_id, "actions": actions})
    return DmActionResult(run_id=run_id, actions=actions, artifact_path=artifact_path)

