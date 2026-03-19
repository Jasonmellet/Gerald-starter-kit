from __future__ import annotations

from typing import Iterable, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Post


def get_by_x_post_id(session: Session, x_post_id: str) -> Optional[Post]:
    return session.execute(select(Post).where(Post.x_post_id == x_post_id)).scalar_one_or_none()


def upsert_from_x_post(session: Session, prospect_id: int, tweet: dict) -> Post:
    x_post_id = tweet["id"]
    existing = get_by_x_post_id(session, x_post_id)
    if existing is None:
        existing = Post(x_post_id=x_post_id, prospect_id=prospect_id, text=tweet.get("text") or "")
        session.add(existing)

    metrics = tweet.get("public_metrics") or {}
    existing.text = tweet.get("text") or existing.text
    created_at_raw = tweet.get("created_at")
    if isinstance(created_at_raw, str):
        try:
            created_dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        except ValueError:
            created_dt = None
    else:
        created_dt = created_at_raw
    if created_dt is not None:
        existing.posted_at = created_dt

    like = metrics.get("like_count")
    reply = metrics.get("reply_count")
    repost = metrics.get("retweet_count")
    quote = metrics.get("quote_count")

    existing.like_count = (like if like is not None else (existing.like_count or 0))
    existing.reply_count = (reply if reply is not None else (existing.reply_count or 0))
    existing.repost_count = (repost if repost is not None else (existing.repost_count or 0))
    existing.quote_count = (quote if quote is not None else (existing.quote_count or 0))
    existing.raw_json = tweet
    return existing


def list_for_prospect(session: Session, prospect_id: int) -> Iterable[Post]:
    return session.scalars(select(Post).where(Post.prospect_id == prospect_id)).all()


