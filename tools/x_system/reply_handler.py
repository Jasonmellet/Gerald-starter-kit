from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .state_manager import StateManager
from .utils import utc_now_compact
from .x_client import XClient


@dataclass
class ReplyActionResult:
    run_id: str
    actions: List[Dict[str, Any]]
    artifact_path: Path


def _build_reply_text(source_text: str) -> str:
    body = source_text.lower()
    if "pipeline" in body or "crm" in body:
        return "Good point. Where does your handoff break most often right now?"
    if "seo" in body or "ppc" in body:
        return "Curious — where do you see the biggest gap right now, traffic quality or conversion path?"
    return "Appreciate you jumping in. What part of this is most painful in your workflow right now?"


def handle_public_replies(
    x_client: XClient,
    classified_items: List[Dict[str, Any]],
    state: StateManager,
    out_dir: Path,
    dry_run: bool,
) -> ReplyActionResult:
    run_id = utc_now_compact()
    actions: List[Dict[str, Any]] = []

    for item in classified_items:
        reply_id = str(item.get("reply_id") or "")
        if not reply_id:
            continue
        label = item.get("classification")
        if label not in {"public_reply_only", "public_reply_dm"}:
            continue
        if state.is_reply_handled(reply_id):
            actions.append({"reply_id": reply_id, "action": "skip_duplicate_reply_handled"})
            continue

        reply_text = _build_reply_text(item.get("text", ""))
        if dry_run:
            action = {
                "reply_id": reply_id,
                "action": "dry_run_reply",
                "reply_text": reply_text,
                "result_id": f"dryrun_reply_{reply_id}",
            }
        else:
            payload = x_client.reply_to_tweet(in_reply_to_tweet_id=reply_id, text=reply_text)
            result_id = payload.get("data", {}).get("id")
            action = {
                "reply_id": reply_id,
                "action": "posted_reply",
                "reply_text": reply_text,
                "result_id": result_id,
            }
        state.mark_reply_handled(reply_id, {"handled_at": run_id, "classification": label, "action": action})
        actions.append(action)

    artifact_path = out_dir / f"reply_actions_{run_id}.json"
    write_json_file(artifact_path, {"run_id": run_id, "actions": actions})
    return ReplyActionResult(run_id=run_id, actions=actions, artifact_path=artifact_path)

