from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from sqlalchemy.orm import Session

from ..models import Prospect


def write_outreach_send_report(
    session: Session,
    run_id: int,
    mode: str,
    summary: Dict[str, object],
    output_dir: Path,
) -> Path:
    """
    Write a markdown report for outreach sending for a given run.
    Timestamp is generated in US Central time.
    """
    from zoneinfo import ZoneInfo

    central = ZoneInfo("America/Chicago")
    now_central = datetime.now(timezone.utc).astimezone(central)
    timestamp = now_central.strftime("%Y%m%d_%H%M%S")
    filename = f"outreach_send_run_{run_id}_{timestamp}.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename

    lines = []
    lines.append(f"# Outreach Send Report: Run {run_id}")
    lines.append("")
    lines.append(f"- **Mode:** {mode}")
    lines.append(f"- **Selected candidates:** {summary.get('selected_candidates')}")
    lines.append(f"- **Attempted sends:** {summary.get('attempted')}")
    lines.append(f"- **Live sent:** {summary.get('live_sent')}")
    lines.append(f"- **Dry-run only:** {summary.get('dry_run')}")
    lines.append(f"- **Skipped:** {summary.get('skipped')}")
    lines.append(f"- **Failed:** {summary.get('failed')}")
    lines.append("")
    lines.append("## Per-prospect details")
    lines.append("")

    details = summary.get("details") or []
    for item in details:  # type: ignore[assignment]
        prospect_id = item.get("prospect_id")
        prospect = session.get(Prospect, prospect_id) if prospect_id is not None else None
        handle = item.get("handle") or (prospect.handle if prospect else f"prospect_{prospect_id}")
        lines.append(f"### @{handle} (prospect_id={prospect_id})")
        lines.append("")
        lines.append(f"- **Status:** {item.get('status')}")
        if "endpoint" in item and item.get("endpoint"):
            lines.append(f"- **Endpoint used:** {item.get('endpoint')}")
        if "participant_id" in item and item.get("participant_id") is not None:
            lines.append(f"- **Participant ID:** {item.get('participant_id')}")
        if "send_result" in item and item.get("send_result") is not None:
            lines.append(f"- **Send result:** {item.get('send_result')}")
        if "reason" in item and item.get("reason"):
            lines.append(f"- **Reason:** {item.get('reason')}")
        if "error" in item and item.get("error"):
            lines.append(f"- **Error:** {item.get('error')}")
        if "opportunity_id" in item and item.get("opportunity_id") is not None:
            lines.append(f"- **Opportunity ID:** {item.get('opportunity_id')}")
        if "x_user_id" in item and item.get("x_user_id"):
            lines.append(f"- **x_user_id:** {item.get('x_user_id')}")
        body = item.get("body")
        if body:
            lines.append("")
            lines.append("```")
            lines.append(str(body))
            lines.append("```")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path

