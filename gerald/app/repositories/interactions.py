from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Interaction


def log_interaction(
    session: Session,
    *,
    prospect_id: int,
    opportunity_id: int | None,
    interaction_type: str,
    notes: str | None = None,
    outcome: str | None = None,
) -> Interaction:
    interaction = Interaction(
        prospect_id=prospect_id,
        opportunity_id=opportunity_id,
        interaction_type=interaction_type,
        notes=notes,
        outcome=outcome,
    )
    session.add(interaction)
    return interaction


def list_for_prospect(session: Session, prospect_id: int) -> Iterable[Interaction]:
    return session.scalars(select(Interaction).where(Interaction.prospect_id == prospect_id)).all()


