from __future__ import annotations

from enum import Enum


class SignalType(str, Enum):
    HIRING_MARKETING = "HIRING_MARKETING"
    FOUNDER_DOING_GTM = "FOUNDER_DOING_GTM"
    RECENT_FUNDING = "RECENT_FUNDING"
    NEEDS_PIPELINE = "NEEDS_PIPELINE"
    MESSAGING_CONFUSION = "MESSAGING_CONFUSION"
    LAUNCHING_SOON = "LAUNCHING_SOON"
    LOW_CONVERSION = "LOW_CONVERSION"
    TOO_MUCH_MANUAL_WORK = "TOO_MUCH_MANUAL_WORK"
    ASKING_FOR_RECOMMENDATIONS = "ASKING_FOR_RECOMMENDATIONS"
    AI_AUTOMATION_INTEREST = "AI_AUTOMATION_INTEREST"
    TEAM_IS_SMALL = "TEAM_IS_SMALL"
    CONTENT_NOT_WORKING = "CONTENT_NOT_WORKING"
    REVOPS_ATTRIBUTION_PAIN = "REVOPS_ATTRIBUTION_PAIN"
    WEBSITE_OR_POSITIONING_WEAKNESS = "WEBSITE_OR_POSITIONING_WEAKNESS"
    GROWTH_STALL_SIGNAL = "GROWTH_STALL_SIGNAL"
    AGENCY_DISSATISFACTION = "AGENCY_DISSATISFACTION"
    FRACTIONAL_HELP_SIGNAL = "FRACTIONAL_HELP_SIGNAL"


class OpportunityStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class DraftChannel(str, Enum):
    DM = "dm"
    REPLY = "reply"
    EMAIL = "email"


class InteractionType(str, Enum):
    NOTE = "note"
    OUTREACH_SENT = "outreach_sent"
    RESPONSE_RECEIVED = "response_received"
    CALL_SCHEDULED = "call_scheduled"
    CALL_COMPLETED = "call_completed"


# ICP keywords for discovery filtering (case-insensitive match on bio)
FOUNDER_KEYWORDS = [
    "founder",
    "cofounder",
    "ceo",
    "cto",
    "co-founder",
    "startup",
    "building",
    "build in public",
    "saas",
    "b2b",
    "product",
    "ai",
    "automation",
    "growth",
    "marketing",
    "revops",
    "operator",
]

NEGATIVE_PROFILE_KEYWORDS = [
    "musician",
    "artist",
    "streamer",
    "vtuber",
    "twitch",
    "youtube creator",
    "content creator",
    "affiliate",
    "giveaway",
    "coupon",
    "deals",
    "etsy",
    "fan account",
    "cosplay",
    "gamer",
]

# Discovery defaults live in config.Settings.discovery_queries

