from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Signal
from ..schemas import SignalExtract


def create_from_extract(
    session: Session,
    prospect_id: int,
    post_id: int | None,
    extract: SignalExtract,
) -> Signal:
    """
    Insert a new Signal row from a parsed SignalExtract.
    Performs simple dedupe on (prospect, signal_type, evidence_text).
    """

    existing = session.execute(
        select(Signal).where(
            Signal.prospect_id == prospect_id,
            Signal.signal_type == extract.signal_type.value,
            Signal.evidence_text == extract.evidence_text,
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    signal = Signal(
        prospect_id=prospect_id,
        post_id=post_id,
        signal_type=extract.signal_type.value,
        signal_strength=extract.signal_strength,
        confidence=extract.confidence,
        evidence_text=extract.evidence_text,
        extracted_pain_point=extract.extracted_pain_point or "",
        extracted_goal=extract.extracted_goal or "",
        rationale=extract.rationale or "",
    )
    session.add(signal)
    return signal


def list_for_prospect(session: Session, prospect_id: int) -> Iterable[Signal]:
    return session.scalars(select(Signal).where(Signal.prospect_id == prospect_id)).all()


