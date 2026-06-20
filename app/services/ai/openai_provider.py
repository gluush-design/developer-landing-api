"""Провайдер на OpenAI Chat Completions (JSON mode)."""
from __future__ import annotations

import logging

from app.schemas.contact import AIAnalysis, ContactRequest
from app.services.ai.base import (
    SYSTEM_PROMPT,
    AIProvider,
    build_user_prompt,
    parse_analysis,
)

logger = logging.getLogger("app.ai.openai")


class OpenAIProvider(AIProvider):
    """Анализ обращения через OpenAI."""

    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        # Импорт внутри — чтобы отсутствие пакета не ломало остальной сервис.
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    async def analyze(self, payload: ContactRequest) -> AIAnalysis:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(payload)},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return parse_analysis(content, provider=self.name)
