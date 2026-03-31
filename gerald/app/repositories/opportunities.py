from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..constants import OpportunityStatus
from ..models import Opportunity
from ..models import REVIEW_STATUS_PENDING
from ..schemas import OpportunityScores


def get_by_id(session: Session, opportunity_id: int) -> Optional[Opportunity]:
    return session.get(Opportunity, opportunity_id)


def get_or_create_for_prospect(session: Session, prospect_id: int) -> Opportunity:
    existing = session.execute(
        select(Opportunity)
        .where(Opportunity.prospect_id == prospect_id)
        .order_by(desc(Opportunity.created_at))
    ).scalar_one_or_none()
    if existing:
        return existing
    opp = Opportunity(
        prospect_id=prospect_id,
        status=OpportunityStatus.NEW.value,
        review_status=REVIEW_STATUS_PENDING,
    )
    session.add(opp)
    return opp


def apply_scores(opportunity: Opportunity, scores: OpportunityScores) -> None:
    opportunity.urgency_score = scores.urgency_score
    opportunity.fit_score = scores.fit_score
    opportunity.buyer_score = scores.buyer_score
    opportunity.outreach_score = scores.outreach_score
    opportunity.confidence_score = scores.confidence_score
    opportunity.overall_score = scores.overall_score
    opportunity.summary = scores.summary
    opportunity.why_now = scores.why_now
    opportunity.recommended_angle = scores.recommended_angle


def list_top_new(session: Session, limit: int = 20) -> Iterable[Opportunity]:
    stmt = (
        select(Opportunity)
        .where(
            Opportunity.status == OpportunityStatus.NEW.value,
            Opportunity.overall_score >= 50,
        )
        .order_by(desc(Opportunity.overall_score))
        .limit(limit)
    )
    return session.scalars(stmt).all()


def count_above_threshold(session: Session, min_overall: float = 50) -> int:
    """Count opportunities with overall_score >= min_overall."""
    from sqlalchemy import func as sqlfunc
    stmt = select(sqlfunc.count(Opportunity.id)).where(Opportunity.overall_score >= min_overall)
    return session.execute(stmt).scalar() or 0


def count_outreach_qualified(session: Session) -> int:
    """Count opportunities that pass outreach qualification (overall>=65, buyer>=60, confidence>=50)."""
    from sqlalchemy import and_, func as sqlfunc
    stmt = (
        select(sqlfunc.count(Opportunity.id))
        .where(
            and_(
                Opportunity.overall_score >= 65,
                Opportunity.buyer_score >= 60,
                Opportunity.confidence_score >= 50,
            )
        )
    )
    return session.execute(stmt).scalar() or 0
