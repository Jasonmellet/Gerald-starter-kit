from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Draft
from ..schemas import DraftOutput

# Sentinel for "not sent" when DB has NOT NULL on sent_at (avoids migration)
UNSENT_SENTINEL = datetime(1970, 1, 1, tzinfo=timezone.utc)


def create_from_output(session: Session, opportunity_id: int, output: DraftOutput) -> Draft:
    draft = Draft(
        opportunity_id=opportunity_id,
        channel=output.channel.value,
        message_type=output.message_type or "dm_intro",
        subject=output.subject or "",
        body=output.body or "",
        personalization_notes=output.personalization_notes or "",
        cta=output.cta or "",
        sent_at=UNSENT_SENTINEL,
    )
    session.add(draft)
    return draft


def list_for_opportunity(session: Session, opportunity_id: int) -> Iterable[Draft]:
    return session.scalars(select(Draft).where(Draft.opportunity_id == opportunity_id)).all()


def count_awaiting_approval(session: Session) -> int:
    """Count drafts that have not been approved."""
    stmt = select(func.count(Draft.id)).where(Draft.approved == False)
    return session.execute(stmt).scalar() or 0


