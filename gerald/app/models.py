from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .constants import DraftChannel, OpportunityStatus, SignalType, InteractionType


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    x_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    handle: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256))
    bio: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(256))
    website: Mapped[str] = mapped_column(String(512))
    follower_count: Mapped[int] = mapped_column(Integer)
    following_count: Mapped[int] = mapped_column(Integer)
    tweet_count: Mapped[int] = mapped_column(Integer)
    account_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    role_guess: Mapped[str] = mapped_column(String(256))
    company_guess: Mapped[str] = mapped_column(String(256))
    fit_notes: Mapped[str] = mapped_column(Text)

    icp_score: Mapped[float] = mapped_column(Float, nullable=True)
    prospect_status: Mapped[str] = mapped_column(String(32), nullable=True)
    discovery_reason: Mapped[str] = mapped_column(Text, nullable=True)
    cannot_receive_dm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="prospect", cascade="all, delete-orphan")
    signals: Mapped[list["Signal"]] = relationship("Signal", back_populates="prospect", cascade="all, delete-orphan")
    opportunities: Mapped[list["Opportunity"]] = relationship(
        "Opportunity", back_populates="prospect", cascade="all, delete-orphan"
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction", back_populates="prospect", cascade="all, delete-orphan"
    )
    contact_history: Mapped[list["ContactHistory"]] = relationship(
        "ContactHistory", back_populates="prospect", cascade="all, delete-orphan"
    )
    run_states: Mapped[list["ProspectRunState"]] = relationship(
        "ProspectRunState", back_populates="prospect", cascade="all, delete-orphan"
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True, nullable=False)
    x_post_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    like_count: Mapped[int] = mapped_column(Integer)
    reply_count: Mapped[int] = mapped_column(Integer)
    repost_count: Mapped[int] = mapped_column(Integer)
    quote_count: Mapped[int] = mapped_column(Integer)

    raw_json = Column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="posts")
    signals: Mapped[list["Signal"]] = relationship("Signal", back_populates="post")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True, nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True, nullable=True)

    signal_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    signal_strength: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_pain_point: Mapped[str] = mapped_column(Text)
    extracted_goal: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="signals")
    post: Mapped["Post"] = relationship("Post", back_populates="signals")


REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(32), index=True, default=OpportunityStatus.NEW.value)
    review_status: Mapped[str] = mapped_column(String(32), index=True, default=REVIEW_STATUS_PENDING, nullable=False)

    overall_score: Mapped[float] = mapped_column(Float)
    urgency_score: Mapped[float] = mapped_column(Float)
    fit_score: Mapped[float] = mapped_column(Float)
    buyer_score: Mapped[float] = mapped_column(Float)
    outreach_score: Mapped[float] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float)

    why_now: Mapped[str] = mapped_column(Text)
    recommended_angle: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="opportunities")
    drafts: Mapped[list["Draft"]] = relationship("Draft", back_populates="opportunity", cascade="all, delete-orphan")
    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction", back_populates="opportunity", cascade="all, delete-orphan"
    )
    contact_history: Mapped[list["ContactHistory"]] = relationship(
        "ContactHistory", back_populates="opportunity", cascade="all, delete-orphan"
    )


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True, nullable=False)

    channel: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    message_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    personalization_notes: Mapped[str] = mapped_column(Text)
    cta: Mapped[str] = mapped_column(Text)

    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_by_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="drafts")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True, nullable=False)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True, nullable=True)

    interaction_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    notes: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="interactions")
    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="interactions")


class ContactHistory(Base):
    __tablename__ = "contact_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True, nullable=False)
    opportunity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("opportunities.id"), index=True, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    message_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    contacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pipeline_runs.id"), index=True, nullable=True)
    send_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    external_message_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    reply_tweet_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reply_skipped_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="contact_history")
    opportunity: Mapped[Optional["Opportunity"]] = relationship("Opportunity", back_populates="contact_history")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovery_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovery_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovery_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyzed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)

    prospect_run_states: Mapped[list["ProspectRunState"]] = relationship(
        "ProspectRunState", back_populates="run", cascade="all, delete-orphan"
    )


class ProspectRunState(Base):
    __tablename__ = "prospect_run_states"
    __table_args__ = (UniqueConstraint("run_id", "prospect_id", name="uq_prospect_run_state_run_prospect"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id"), index=True, nullable=False)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True, nullable=False)
    included_in_discovery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    selected_for_outreach: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    excluded_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    freshness_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="prospect_run_states")
    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="run_states")


