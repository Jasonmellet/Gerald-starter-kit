from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ContactHistory


def record_contact(
    session: Session,
    prospect_id: int,
    channel: str,
    opportunity_id: Optional[int] = None,
    message_hash: Optional[str] = None,
    run_id: Optional[int] = None,
    model_used: Optional[str] = None,
    send_status: Optional[str] = None,
    external_message_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> ContactHistory:
    rec = ContactHistory(
        prospect_id=prospect_id,
        opportunity_id=opportunity_id,
        channel=channel,
        message_hash=message_hash,
        contacted_at=datetime.now(timezone.utc),
        run_id=run_id,
        model_used=model_used,
        send_status=send_status,
        external_message_id=external_message_id,
        error_message=error_message,
    )
    session.add(rec)
    return rec


def recently_contacted(
    session: Session,
    prospect_id: int,
    within_days: int = 30,
) -> bool:
    """
    True if this prospect has been contacted within the last within_days days
    **with a real send** (send_status == 'sent'). Dry-run contacts do not suppress.
    """
    since = datetime.now(timezone.utc) - timedelta(days=within_days)
    stmt = (
        select(ContactHistory)
        .where(ContactHistory.prospect_id == prospect_id)
        .where(ContactHistory.contacted_at >= since)
        .where(
            (ContactHistory.send_status == "sent") | (ContactHistory.send_status.is_(None))
        )
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def list_sent_without_reply_for_run(session: Session, run_id: int) -> List[ContactHistory]:
    """Contacts for this run that were sent (DM), have no reply yet, and were not skipped (e.g. X policy)."""
    stmt = (
        select(ContactHistory)
        .where(ContactHistory.run_id == run_id)
        .where(ContactHistory.send_status == "sent")
        .where(ContactHistory.reply_tweet_id.is_(None))
        .where(ContactHistory.reply_skipped_reason.is_(None))
        .order_by(ContactHistory.contacted_at.asc())
    )
    return list(session.execute(stmt).scalars().all())


def set_reply_tweet_id(session: Session, contact_id: int, reply_tweet_id: str) -> None:
    """Record that we posted a follow-up reply tweet for this contact."""
    rec = session.get(ContactHistory, contact_id)
    if rec:
        rec.reply_tweet_id = reply_tweet_id
        session.flush()


def set_reply_skipped_reason(session: Session, contact_id: int, reason: str) -> None:
    """Record that we skipped follow-up reply (e.g. X policy 403); we won't retry this contact."""
    rec = session.get(ContactHistory, contact_id)
    if rec:
        rec.reply_skipped_reason = reason
        session.flush()
