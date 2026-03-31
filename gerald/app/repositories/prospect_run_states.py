from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Opportunity, ProspectRunState


def add_to_run(
    session: Session,
    run_id: int,
    prospect_id: int,
    included_in_discovery: bool = True,
) -> ProspectRunState:
    existing = session.execute(
        select(ProspectRunState).where(
            ProspectRunState.run_id == run_id,
            ProspectRunState.prospect_id == prospect_id,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    state = ProspectRunState(
        run_id=run_id,
        prospect_id=prospect_id,
        included_in_discovery=included_in_discovery,
    )
    session.add(state)
    return state


def get_state(session: Session, run_id: int, prospect_id: int) -> Optional[ProspectRunState]:
    return session.execute(
        select(ProspectRunState).where(
            ProspectRunState.run_id == run_id,
            ProspectRunState.prospect_id == prospect_id,
        )
    ).scalar_one_or_none()


def list_prospect_ids_for_run(
    session: Session,
    run_id: int,
    only_discovered: bool = True,
    only_analyzed: bool = False,
    only_scored: bool = False,
) -> List[int]:
    stmt = select(ProspectRunState.prospect_id).where(ProspectRunState.run_id == run_id)
    if only_discovered:
        stmt = stmt.where(ProspectRunState.included_in_discovery == True)
    if only_analyzed:
        stmt = stmt.where(ProspectRunState.analyzed == True)
    if only_scored:
        stmt = stmt.where(ProspectRunState.scored == True)
    rows = session.execute(stmt).scalars().all()
    return list(rows)


def mark_analyzed(session: Session, run_id: int, prospect_id: int) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.analyzed = True


def mark_scored(session: Session, run_id: int, prospect_id: int) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.scored = True


def mark_selected(session: Session, run_id: int, prospect_id: int, priority_score: Optional[float] = None) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.selected_for_outreach = True
        if priority_score is not None:
            state.priority_score = priority_score


def mark_sent(session: Session, run_id: int, prospect_id: int) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.sent = True


def set_excluded(session: Session, run_id: int, prospect_id: int, reason: str) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.excluded_reason = reason


def set_freshness(session: Session, run_id: int, prospect_id: int, hours: float) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.freshness_hours = hours


def set_priority_score(session: Session, run_id: int, prospect_id: int, score: float) -> None:
    state = get_state(session, run_id, prospect_id)
    if state:
        state.priority_score = score


def list_selected_for_run(session: Session, run_id: int) -> List[ProspectRunState]:
    stmt = (
        select(ProspectRunState)
        .where(ProspectRunState.run_id == run_id)
        .where(ProspectRunState.selected_for_outreach == True)
    )
    return list(session.execute(stmt).scalars().all())


def list_states_for_run(session: Session, run_id: int, only_scored: bool = False) -> List[ProspectRunState]:
    stmt = select(ProspectRunState).where(ProspectRunState.run_id == run_id)
    if only_scored:
        stmt = stmt.where(ProspectRunState.scored == True)
    return list(session.execute(stmt).scalars().all())


def count_discovered_for_run(session: Session, run_id: int) -> int:
    from sqlalchemy import func
    stmt = select(func.count(ProspectRunState.id)).where(
        ProspectRunState.run_id == run_id,
        ProspectRunState.included_in_discovery == True,
    )
    return session.execute(stmt).scalar() or 0


def count_analyzed_for_run(session: Session, run_id: int) -> int:
    from sqlalchemy import func
    stmt = select(func.count(ProspectRunState.id)).where(
        ProspectRunState.run_id == run_id,
        ProspectRunState.analyzed == True,
    )
    return session.execute(stmt).scalar() or 0


def count_scored_for_run(session: Session, run_id: int) -> int:
    from sqlalchemy import func
    stmt = select(func.count(ProspectRunState.id)).where(
        ProspectRunState.run_id == run_id,
        ProspectRunState.scored == True,
    )
    return session.execute(stmt).scalar() or 0
