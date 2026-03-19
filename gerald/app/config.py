from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR.parent / ".env"

# Load .env if present (non-fatal if missing)
load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    database_url: str = Field(default="sqlite:///./gerald.db", validation_alias="DATABASE_URL")

    x_bearer_token: Optional[str] = Field(default=None, validation_alias="X_BEARER_TOKEN")
    # OAuth 2.0 user access token (Bearer) for posting tweets/replies; doc: https://docs.x.com/llms.txt
    x_user_access_token: Optional[str] = Field(default=None, validation_alias="X_USER_ACCESS_TOKEN")
    x_api_key: Optional[str] = Field(default=None, validation_alias="X_API_KEY")
    x_api_secret: Optional[str] = Field(default=None, validation_alias="X_API_SECRET")
    x_access_token: Optional[str] = Field(default=None, validation_alias="X_ACCESS_TOKEN")
    x_access_token_secret: Optional[str] = Field(default=None, validation_alias="X_ACCESS_TOKEN_SECRET")

    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    # 2026 lineup: Haiku 4.5 (budget), Sonnet 4.6 (balanced), Opus 4.6 (performance)
    anthropic_cheap_model: str = Field(
        default="claude-haiku-4-5",
        validation_alias="ANTHROPIC_CHEAP_MODEL",
    )
    anthropic_strong_model: str = Field(
        default="claude-sonnet-4-6",
        validation_alias="ANTHROPIC_STRONG_MODEL",
    )
    anthropic_performance_model: str = Field(
        default="claude-opus-4-6",
        validation_alias="ANTHROPIC_PERFORMANCE_MODEL",
    )

    default_lookback_days: int = Field(default=7, validation_alias="DEFAULT_LOOKBACK_DAYS")
    default_max_prospects: int = Field(default=25, validation_alias="DEFAULT_MAX_PROSPECTS")

    discovery_lookback_hours: int = Field(default=30, validation_alias="DISCOVERY_LOOKBACK_HOURS")
    daily_discovery_limit: int = Field(default=100, validation_alias="DAILY_DISCOVERY_LIMIT")
    daily_outreach_limit: int = Field(default=5, validation_alias="DAILY_OUTREACH_LIMIT")
    recent_contact_suppression_days: int = Field(
        default=30,
        validation_alias="RECENT_CONTACT_SUPPRESSION_DAYS",
    )
    outreach_send_mode: str = Field(
        default="dry_run",
        validation_alias="OUTREACH_SEND_MODE",
    )
    allow_live_send: bool = Field(
        default=False,
        validation_alias="ALLOW_LIVE_SEND",
    )
    follow_up_reply_enabled: bool = Field(
        default=True,
        validation_alias="FOLLOW_UP_REPLY_ENABLED",
    )
    follow_up_reply_delay_seconds: int = Field(
        default=300,
        validation_alias="FOLLOW_UP_REPLY_DELAY_SECONDS",
    )
    default_max_posts_per_user: int = Field(default=20, validation_alias="DEFAULT_MAX_POSTS_PER_USER")

    discovery_queries: List[str] = Field(
        default_factory=lambda: [
            "hiring first marketer",
            "looking for a marketer",
            "need help with growth",
            "need more pipeline",
            "our funnel",
            "attribution is broken",
            "marketing isn't working",
            "launching soon",
            "seed round",
            "series a",
            "hiring growth",
            "hiring marketing",
            "b2b saas",
            "building in public",
            "ai startup",
        ]
    )

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Use this instead of instantiating Settings directly so that configuration
    is loaded and validated once per process.
    """

    return Settings()


