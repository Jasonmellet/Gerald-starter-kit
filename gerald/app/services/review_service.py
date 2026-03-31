from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Iterable, List

from rich.console import Console
from rich.table import Table

from ..constants import OpportunityStatus
from ..db import get_session
from ..logging import get_logger
from ..models import Opportunity
from ..models import REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED
from ..repositories import drafts as drafts_repo
from ..repositories import interactions as interactions_repo
from ..repositories import opportunities as opp_repo


logger = get_logger(__name__)
console = Console()


def list_opportunities(limit: int = 20) -> List[Opportunity]:
    with get_session() as session:
        return list(opp_repo.list_top_new(session, limit=limit))


def render_opportunities_table(opportunities: Iterable[Opportunity]) -> None:
    table = Table(title="Gerald Opportunities")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Handle")
    table.add_column("Status")
    table.add_column("Review")
    table.add_column("Overall")
    table.add_column("Urgency")
    table.add_column("Fit")
    table.add_column("Buyer")
    table.add_column("Outreach")
    table.add_column("Conf")

    for opp in opportunities:
        p = opp.prospect
        table.add_row(
            str(opp.id),
            p.handle if p else "?",
            opp.status or "",
            getattr(opp, "review_status", "") or "pending",
            f"{opp.overall_score or 0:.1f}",
            f"{opp.urgency_score or 0:.1f}",
            f"{opp.fit_score or 0:.1f}",
            f"{opp.buyer_score or 0:.1f}",
            f"{opp.outreach_score or 0:.1f}",
            f"{opp.confidence_score or 0:.1f}",
        )

    console.print(table)


def _update_status(opportunity_id: int, new_status: OpportunityStatus) -> None:
    with get_session() as session:
        opp = opp_repo.get_by_id(session, opportunity_id)
        if not opp:
            console.print(f"[red]Opportunity {opportunity_id} not found[/red]")
            return
        opp.status = new_status.value
        if new_status == OpportunityStatus.APPROVED:
            opp.review_status = REVIEW_STATUS_APPROVED
        elif new_status == OpportunityStatus.REJECTED:
            opp.review_status = REVIEW_STATUS_REJECTED
        interactions_repo.log_interaction(
            session,
            prospect_id=opp.prospect_id,
            opportunity_id=opp.id,
            interaction_type=f"status_{new_status.value}",
            notes=None,
        )
        session.commit()
        console.print(f"[green]Updated opportunity {opportunity_id} to {new_status.value}[/green]")


def approve_opportunity(opportunity_id: int) -> None:
    _update_status(opportunity_id, OpportunityStatus.APPROVED)


def reject_opportunity(opportunity_id: int) -> None:
    _update_status(opportunity_id, OpportunityStatus.REJECTED)


def archive_opportunity(opportunity_id: int) -> None:
    _update_status(opportunity_id, OpportunityStatus.ARCHIVED)


def mark_draft_human_edited(draft_id: int) -> None:
    from ..models import Draft
    from ..db import get_session as _get_session

    with _get_session() as session:
        draft = session.get(Draft, draft_id)
        if not draft:
            console.print(f"[red]Draft {draft_id} not found[/red]")
            return
        draft.edited_by_human = True
        session.commit()
        console.print(f"[green]Marked draft {draft_id} as human-edited[/green]")


def edit_opportunity_draft(opportunity_id: int) -> None:
    """Open the opportunity's DM draft in $EDITOR and save changes."""
    from ..models import Draft

    with get_session() as session:
        opp = opp_repo.get_by_id(session, opportunity_id)
        if not opp:
            console.print(f"[red]Opportunity {opportunity_id} not found[/red]")
            return
        drafts = list(drafts_repo.list_for_opportunity(session, opp.id))
        dm_draft = next((d for d in drafts if d.channel == "dm"), None)
        if not dm_draft:
            console.print(f"[red]No DM draft found for opportunity {opportunity_id}. Run draft first.[/red]")
            return
        body = (dm_draft.body or "").strip()
        editor = os.environ.get("EDITOR", "nano")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(body)
            path = f.name
        try:
            subprocess.run([editor, path], check=False)
            with open(path, "r") as f:
                new_body = f.read().strip()
            dm_draft.body = new_body or dm_draft.body
            dm_draft.edited_by_human = True
            session.commit()
            console.print(f"[green]Updated draft for opportunity {opportunity_id}[/green]")
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


