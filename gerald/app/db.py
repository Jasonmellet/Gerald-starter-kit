from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import get_settings


Base = declarative_base()


def _get_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # Needed for SQLite in multi-threaded contexts (e.g. Typer + rich)
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args, future=True)


engine = _get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Provide a transactional scope around a series of operations.
    """

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _migrate_sqlite_opportunities_review_status() -> None:
    """Add opportunities.review_status if missing (existing DBs)."""
    if not engine.url.drivername.startswith("sqlite"):
        return
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(opportunities)"))
        rows = result.fetchall()
        # rows are (cid, name, type, notnull, default_value, pk)
        if not rows:
            return
        names = [row[1] for row in rows]
        if "review_status" in names:
            return
        conn.execute(
            text(
                "ALTER TABLE opportunities ADD COLUMN review_status VARCHAR(32) DEFAULT 'pending' NOT NULL"
            )
        )
        conn.commit()


def _migrate_sqlite_prospects_cannot_receive_dm() -> None:
    """Add prospects.cannot_receive_dm if missing (tag when X returns 403 DM not allowed)."""
    if not engine.url.drivername.startswith("sqlite"):
        return
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(prospects)"))
        rows = result.fetchall()
        if not rows:
            return
        names = [row[1] for row in rows]
        if "cannot_receive_dm" in names:
            return
        conn.execute(
            text("ALTER TABLE prospects ADD COLUMN cannot_receive_dm BOOLEAN NOT NULL DEFAULT 0")
        )
        conn.commit()


def _migrate_sqlite_contact_history_reply_tweet_id() -> None:
    """Add contact_history.reply_tweet_id if missing (follow-up reply tweet id)."""
    if not engine.url.drivername.startswith("sqlite"):
        return
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(contact_history)"))
        rows = result.fetchall()
        if not rows:
            return
        names = [row[1] for row in rows]
        if "reply_tweet_id" in names:
            return
        conn.execute(
            text("ALTER TABLE contact_history ADD COLUMN reply_tweet_id VARCHAR(64)")
        )
        conn.commit()


def _migrate_sqlite_contact_history_reply_skipped_reason() -> None:
    """Add contact_history.reply_skipped_reason if missing (skip future reply attempts when X policy blocks)."""
    if not engine.url.drivername.startswith("sqlite"):
        return
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(contact_history)"))
        rows = result.fetchall()
        if not rows:
            return
        names = [row[1] for row in rows]
        if "reply_skipped_reason" in names:
            return
        conn.execute(
            text("ALTER TABLE contact_history ADD COLUMN reply_skipped_reason VARCHAR(64)")
        )
        conn.commit()


def run_migrations() -> None:
    """Run one-off migrations for existing DBs (e.g. new columns, new tables). Safe to call on every startup."""
    _migrate_sqlite_opportunities_review_status()
    _migrate_sqlite_prospects_cannot_receive_dm()
    _migrate_sqlite_contact_history_reply_tweet_id()
    _migrate_sqlite_contact_history_reply_skipped_reason()
    # Create any new tables (e.g. contact_history) that don't exist yet. Idempotent.
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def create_all() -> None:
    """
    Create all database tables based on SQLAlchemy models.

    Intended for initial setup and local development; not a replacement
    for real migrations in a production environment.
    """

    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    run_migrations()


