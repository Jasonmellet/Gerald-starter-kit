from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel

from ..db import get_session
from ..logging import get_logger
from ..models import Opportunity
from ..repositories import drafts as drafts_repo
from ..repositories import opportunities as opp_repo
from ..repositories import signals as signals_repo


logger = get_logger(__name__)
console = Console()
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"


def _tier_label(score: float) -> str:
    if score >= 70:
        return "Tier 1"
    if score >= 60:
        return "Tier 2"
    return "Tier 3"


def build_digest(top_n: int = 20, run_id: Optional[str] = None) -> None:
    with get_session() as session:
        opps: List[Opportunity] = list(opp_repo.list_top_new(session, limit=top_n))

        lines: List[str] = ["# Gerald Daily Digest", ""]

        for opp in opps:
            p = opp.prospect
            drafts = list(drafts_repo.list_for_opportunity(session, opp.id))
            dm_preview = next((d.body for d in drafts if d.channel == "dm"), None)

            handle = p.handle if p else "?"
            name = p.display_name or ""
            role = (p.role_guess or "").strip()
            company = (p.company_guess or "").strip()
            if role or company:
                role_company_line = f"- Role/company: {role} at {company}".strip()
            else:
                role_company_line = "- Role/company: —"

            lines.append(f"## @{handle} — {name}")
            lines.append(role_company_line)
            lines.append(f"- Main pain: {opp.summary or 'N/A'}")
            lines.append(f"- Recommended angle: {opp.recommended_angle or 'N/A'}")

            # Evidence: bullet points from signals
            if p:
                signals = list(signals_repo.list_for_prospect(session, p.id))
                if signals:
                    lines.append("- Evidence:")
                    for s in signals[:10]:
                        ev = (s.evidence_text or "").strip()
                        if ev:
                            lines.append(f"  • \"{ev}\"")

            lines.append(
                "- Scores: overall "
                f"{opp.overall_score or 0:.1f} "
                f"(urgency {opp.urgency_score or 0:.1f}, "
                f"fit {opp.fit_score or 0:.1f}, "
                f"buyer {opp.buyer_score or 0:.1f}, "
                f"outreach {opp.outreach_score or 0:.1f}, "
                f"confidence {opp.confidence_score or 0:.1f})"
            )
            if dm_preview:
                preview_line = dm_preview.splitlines()[0][:140]
                lines.append(f"- DM preview: \"{preview_line}\"")

            score_val = opp.overall_score or 0
            lines.append(f"- Priority: {_tier_label(score_val)}")
            lines.append("")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_label = run_id or ts

        per_run_path = OUTPUT_DIR / f"daily_digest_{run_label}.md"
        per_run_path.write_text("\n".join(lines), encoding="utf-8")

        # Also keep a stable "latest" file for convenience.
        latest_path = OUTPUT_DIR / "daily_digest.md"
        latest_path.write_text("\n".join(lines), encoding="utf-8")

        logger.info("Digest written", extra={"run_id": run_label, "output_path": str(per_run_path)})
        console.print(Panel.fit(f"Wrote daily digest to {per_run_path}", style="green"))

