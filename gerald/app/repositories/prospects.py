from __future__ import annotations

from typing import Iterable, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Prospect


def get_by_x_user_id(session: Session, x_user_id: str) -> Optional[Prospect]:
    return session.execute(select(Prospect).where(Prospect.x_user_id == x_user_id)).scalar_one_or_none()


def get_by_handle(session: Session, handle: str) -> Optional[Prospect]:
    return session.execute(select(Prospect).where(Prospect.handle == handle)).scalar_one_or_none()


def upsert_from_x_profile(session: Session, profile: dict) -> Prospect:
    """
    Create or update a Prospect from an X user profile payload.
    """

    x_user_id = profile["id"]
    handle = profile.get("username") or profile.get("screen_name") or ""
    existing = get_by_x_user_id(session, x_user_id)

    if existing is None:
        existing = Prospect(x_user_id=x_user_id, handle=handle)
        session.add(existing)

    metrics = (profile.get("public_metrics") or {}) if isinstance(profile, dict) else {}
    existing.handle = handle
    existing.display_name = profile.get("name") or existing.display_name
    existing.bio = profile.get("description") or existing.bio or ""
    # Some schemas mark location non-nullable; default to empty string if missing.
    existing.location = profile.get("location") or existing.location or ""
    # Ensure website is never NULL for schemas that mark it non-nullable.
    existing.website = profile.get("url") or existing.website or ""
    followers = metrics.get("followers_count")
    following = metrics.get("following_count")
    tweets = metrics.get("tweet_count")

    existing.follower_count = followers if followers is not None else (existing.follower_count or 0)
    existing.following_count = following if following is not None else (existing.following_count or 0)
    existing.tweet_count = tweets if tweets is not None else (existing.tweet_count or 0)

    created_at_raw = profile.get("created_at")
    if isinstance(created_at_raw, str):
        try:
            created_dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        except ValueError:
            created_dt = None
    else:
        created_dt = created_at_raw

    if created_dt is not None:
        existing.account_created_at = created_dt

    # Ensure optional enrichment fields are never NULL for schemas that mark them non-nullable.
    existing.role_guess = existing.role_guess or ""
    existing.company_guess = existing.company_guess or ""
    existing.fit_notes = existing.fit_notes or ""

    return existing


def list_all(
    session: Session,
    limit: Optional[int] = None,
    min_icp_score: Optional[float] = None,
) -> Iterable[Prospect]:
    stmt = select(Prospect)
    if min_icp_score is not None:
        stmt = stmt.where(Prospect.icp_score >= min_icp_score)
    if limit is not None:
        stmt = stmt.limit(limit)
    return session.scalars(stmt).all()


