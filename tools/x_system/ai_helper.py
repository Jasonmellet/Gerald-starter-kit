from __future__ import annotations

import os
from typing import Dict, Optional


class AIHelper:
    """
    Optional helper only. If unavailable/failing, caller should ignore and continue.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def improve_post(self, text: str, context: Optional[Dict[str, str]] = None) -> Optional[str]:
        if not self.enabled:
            return None
        if not self.api_key:
            return None
        # Deterministic-safe stub: keep external dependence optional.
        # This can be upgraded later to real API calls without changing pipeline flow.
        context = context or {}
        tightened = text.strip()
        if len(tightened) > 275:
            tightened = tightened[:272].rstrip() + "..."
        # Light rewrite heuristic when AI mode is enabled:
        if "Most SMBs" not in tightened and context.get("topic"):
            tightened = f"{tightened}\n\n({context['topic']} operator note)"
        return tightened

    def classify_reply_hint(self, reply_text: str) -> Optional[str]:
        if not self.enabled or not self.api_key:
            return None
        body = reply_text.lower()
        if "help" in body or "struggle" in body:
            return "public_reply_dm"
        if len(body.strip()) < 8:
            return "ignore"
        return "public_reply_only"

