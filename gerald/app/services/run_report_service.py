from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from ..models import PipelineRun, Prospect
from ..repositories import prospect_run_states as run_states_repo


def write_run_report(session, run: PipelineRun, output_dir: Path) -> Path:
    """
    Write a markdown report for the run to output_dir.
    Path: outputs/daily_run_<run_id>_<timestamp>.md (timestamp in US Central time)
    """
    central = ZoneInfo("America/Chicago")
    now_central = datetime.now(timezone.utc).astimezone(central)
    timestamp = now_central.strftime("%Y%m%d_%H%M%S")
    filename = f"daily_run_{run.id}_{timestamp}.md"
    path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    window_start_c = run.discovery_window_start.astimezone(central)
    window_end_c = run.discovery_window_end.astimezone(central)

    lines = [
        f"# Daily Run Report: Run {run.id}",
        "",
        f"- **Window (US Central):** {window_start_c} — {window_end_c}",
        f"- **Discovery limit:** {run.discovery_limit}",
        f"- **Discovered:** {run.discovered_count or 0}",
        f"- **Analyzed:** {run.analyzed_count or 0}",
        f"- **Scored:** {run.scored_count or 0}",
        f"- **Selected:** {run.selected_count or 0}",
        f"- **Sent:** {run.sent_count or 0}",
        f"- **Total estimated cost:** {run.total_estimated_cost}",
        f"- **Status:** {run.status}",
        "",
        "## Top selected",
        "",
    ]

    selected_states = run_states_repo.list_selected_for_run(session, run.id)
    for state in selected_states:
        prospect = session.get(Prospect, state.prospect_id)
        handle = prospect.handle if prospect else f"prospect_{state.prospect_id}"
        score = state.priority_score if state.priority_score is not None else ""
        freshness = f"{state.freshness_hours:.1f}h" if state.freshness_hours is not None else ""
        lines.append(f"- @{handle} — priority_score={score}, freshness={freshness}")
    if not selected_states:
        lines.append("- (none)")
    lines.append("")

    # Skipped / excluded summary
    all_states = run_states_repo.list_states_for_run(session, run.id)
    excluded = [s for s in all_states if s.excluded_reason]
    if excluded:
        lines.append("## Skipped (excluded reasons)")
        lines.append("")
        from collections import Counter
        reasons = Counter(s.excluded_reason for s in excluded if s.excluded_reason)
        for reason, count in reasons.most_common():
            lines.append(f"- {reason}: {count}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
