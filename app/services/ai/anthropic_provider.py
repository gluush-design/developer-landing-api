"""Провайдер на Anthropic Claude (Messages API)."""
from __future__ import annotations

import logging

from app.schemas.contact import AIAnalysis, ContactRequest
from app.services.ai.base import (
    SYSTEM_PROMPT,
    AIProvider,
    build_user_prompt,
    parse_analysis,
)

logger = logging.getLogger("app.ai.anthropic")


class AnthropicProvider(AIProvider):
    """Анализ обращения через Claude."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        self._model = model

    async def analyze(self, payload: ContactRequest) -> AIAnalysis:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=600,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(payload)}],
        )
        # У Claude ответ — список блоков; берём текстовые.
        content = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return parse_analysis(content, provider=self.name)
