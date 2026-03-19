from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from .constants import SignalType, DraftChannel, OpportunityStatus


class SignalExtract(BaseModel):
    signal_type: SignalType
    confidence: float = Field(ge=0.0, le=1.0)
    signal_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_text: str
    extracted_pain_point: Optional[str] = None
    extracted_goal: Optional[str] = None
    rationale: Optional[str] = None


class ProspectSummary(BaseModel):
    role_guess: Optional[str] = None
    company_guess: Optional[str] = None
    summary: str
    fit_notes: Optional[str] = None


class OpportunityScores(BaseModel):
    urgency_score: float = Field(ge=0.0, le=100.0)
    fit_score: float = Field(ge=0.0, le=100.0)
    buyer_score: float = Field(ge=0.0, le=100.0)
    outreach_score: float = Field(ge=0.0, le=100.0)
    confidence_score: float = Field(ge=0.0, le=100.0)
    overall_score: Optional[float] = None

    summary: str
    why_now: Optional[str] = None
    recommended_angle: Optional[str] = None

    @field_validator("overall_score", mode="after")
    @classmethod
    def compute_overall_if_missing(cls, v, values):
        if v is not None:
            return v
        urg = values.data["urgency_score"]
        fit = values.data["fit_score"]
        buyer = values.data["buyer_score"]
        outreach = values.data["outreach_score"]
        conf = values.data["confidence_score"]
        return 0.30 * urg + 0.25 * fit + 0.20 * buyer + 0.15 * outreach + 0.10 * conf


class DraftOutput(BaseModel):
    channel: DraftChannel
    message_type: str
    subject: Optional[str] = None
    body: str
    personalization_notes: Optional[str] = None
    cta: Optional[str] = None
    recommended_angle: Optional[str] = None


class DigestItem(BaseModel):
    prospect_handle: str
    prospect_display_name: Optional[str] = None
    role_guess: Optional[str] = None
    company_guess: Optional[str] = None
    main_pain_point: Optional[str] = None
    recommended_angle: Optional[str] = None
    score_overall: float
    score_urgency: float
    score_fit: float
    score_buyer: float
    score_outreach: float
    score_confidence: float
    dm_preview: Optional[str] = None
    priority_recommendation: Optional[str] = None


