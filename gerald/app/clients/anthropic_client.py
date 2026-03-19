from __future__ import annotations

from typing import Any, Dict

import anthropic

from ..config import get_settings
from ..logging import get_logger


logger = get_logger(__name__)


class AnthropicClientError(Exception):
    pass


class AnthropicClient:
    """
    Thin wrapper around Anthropic to expose cheap/strong completion helpers.

    Uses Messages API and expects prompts defined in app/prompts.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise AnthropicClientError("ANTHROPIC_API_KEY is not configured.")

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._cheap_model = settings.anthropic_cheap_model
        self._strong_model = settings.anthropic_strong_model
        self._performance_model = settings.anthropic_performance_model

    def _complete(
        self,
        *,
        model: str,
        system: str,
        user_content: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        try:
            msg = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
                temperature=temperature,
            )
        except Exception as exc:  # pragma: no cover - surfaced via logging
            logger.error("Anthropic API error", extra={"model": model, "error": str(exc)})
            raise AnthropicClientError(str(exc)) from exc

        # Messages API returns a list of content blocks; join text parts
        parts = []
        for block in msg.content:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts).strip()

    def cheap_complete(self, system: str, user_content: str, **kwargs: Any) -> str:
        return self._complete(
        model=self._cheap_model,
        system=system,
        user_content=user_content,
        **kwargs,
    )

    def strong_complete(self, system: str, user_content: str, **kwargs: Any) -> str:
        return self._complete(
            model=self._strong_model,
            system=system,
            user_content=user_content,
            **kwargs,
        )

    def performance_complete(self, system: str, user_content: str, **kwargs: Any) -> str:
        return self._complete(
            model=self._performance_model,
            system=system,
            user_content=user_content,
            **kwargs,
        )


