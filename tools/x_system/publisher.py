from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from .config import write_json_file
from .utils import utc_now_compact
from .x_client import XClient


@dataclass
class PublishResult:
    run_id: str
    post_id: str
    posted_text: str
    artifact_path: Path


def publish_winner(
    x_client: XClient,
    winner: Dict[str, Any],
    out_dir: Path,
    dry_run: bool,
) -> PublishResult:
    run_id = utc_now_compact()
    text = winner.get("text", "").strip()
    if not text:
        raise ValueError("No winner text to publish")

    if dry_run:
        post_id = f"dryrun_{run_id}"
        api_payload: Dict[str, Any] = {"data": {"id": post_id, "text": text}}
    else:
        api_payload = x_client.create_post(text)
        post_id = api_payload.get("data", {}).get("id")
        if not post_id:
            raise ValueError("X API did not return a post ID")

    record = {
        "run_id": run_id,
        "post_id": post_id,
        "posted_text": text,
        "winner_context": winner,
        "source_topic": winner.get("topic"),
        "published_at_utc": run_id,
        "dry_run": dry_run,
        "api_payload": api_payload,
    }
    artifact_path = out_dir / f"publish_{run_id}.json"
    write_json_file(artifact_path, record)
    return PublishResult(run_id=run_id, post_id=post_id, posted_text=text, artifact_path=artifact_path)

