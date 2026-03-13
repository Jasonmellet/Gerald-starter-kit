from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import write_json_file
from .utils import utc_now_compact
from .x_client import XClient


@dataclass
class MonitorResult:
    run_id: str
    post_id: str
    replies: List[Dict[str, Any]]
    artifact_path: Path


def monitor_replies(
    x_client: XClient,
    post_id: str,
    out_dir: Path,
    dry_run: bool,
    poll_interval_seconds: int,
    max_window_seconds: int,
) -> MonitorResult:
    """
    Bounded monitoring (configurable). Polls repeatedly and returns collected replies.
    In dry-run mode we do one immediate fetch to avoid long waits.
    """
    import time

    run_id = utc_now_compact()
    replies: List[Dict[str, Any]] = []
    seen_ids = set()

    if dry_run:
        # In dry-run, do not hit live reply search for synthetic post IDs.
        loops = 0
    elif max_window_seconds <= 0:
        # One-pass execution mode for scheduler-driven monitoring.
        loops = 1
    else:
        loops = max(1, int(max_window_seconds / max(1, poll_interval_seconds)))

    for i in range(loops):
        chunk = x_client.search_replies(tweet_id=post_id, max_results=100)
        for reply in chunk:
            rid = reply.get("id")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                replies.append(reply)
        if i < loops - 1 and not dry_run:
            time.sleep(poll_interval_seconds)

    artifact_path = out_dir / f"replies_{run_id}.json"
    write_json_file(
        artifact_path,
        {
            "run_id": run_id,
            "post_id": post_id,
            "dry_run": dry_run,
            "poll_interval_seconds": poll_interval_seconds,
            "max_window_seconds": max_window_seconds,
            "replies": replies,
        },
    )
    return MonitorResult(run_id=run_id, post_id=post_id, replies=replies, artifact_path=artifact_path)

