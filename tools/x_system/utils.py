from __future__ import annotations

from datetime import datetime, timezone


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

