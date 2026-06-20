"""AIAnalyzer — фасад анализа обращений с graceful fallback.

Логика: пробуем основной провайдер (OpenAI/Anthropic) с таймаутом; при любой
ошибке (нет ключа, сеть, таймаут, кривой JSON) — мягко падаем на rule-based
FallbackProvider. Сервис обработки обращения НИКОГДА не падает из-за AI.
"""
from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.schemas.contact import AIAnalysis, ContactRequest
from app.services.ai.base import AIProvider
from app.services.ai.fallback_provider import FallbackProvider

logger = logging.getLogger("app.ai")


class AIAnalyzer:
    """Оркестратор: основной провайдер + гарантированный fallback."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = settings.ai_timeout_seconds
        self._fallback = FallbackProvider()
        self._primary: AIProvider | None = self._build_primary(settings)

    @staticmethod
    def _build_primary(settings: Settings) -> AIProvider | None:
        """Инициализировать основной провайдер, если он сконфигурирован."""
        try:
            if settings.ai_provider == "openai" and settings.openai_api_key:
                from app.services.ai.openai_provider import OpenAIProvider

                return OpenAIProvider(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    timeout=settings.ai_timeout_seconds,
                )
            if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
                from app.services.ai.anthropic_provider import AnthropicProvider

                return AnthropicProvider(
                    api_key=settings.anthropic_api_key,
                    model=settings.anthropic_model,
                    timeout=settings.ai_timeout_seconds,
                )
        except Exception as exc:  # noqa: BLE001 — инициализация не должна ронять сервис
            logger.warning("Не удалось инициализировать AI-провайдера: %s", exc)
        return None

    @property
    def active_provider(self) -> str:
        return self._primary.name if self._primary else self._fallback.name

    async def analyze(self, payload: ContactRequest) -> AIAnalysis:
        """Вернуть анализ обращения. Всегда успешен (в крайнем случае fallback)."""
        if self._primary is not None:
            try:
                analysis = await asyncio.wait_for(
                    self._primary.analyze(payload), timeout=self._timeout
                )
                logger.info(
                    "AI-анализ выполнен провайдером '%s'", self._primary.name
                )
                return analysis
            except asyncio.TimeoutError:
                logger.warning(
                    "AI-провайдер '%s' превысил таймаут %.1fs — fallback",
                    self._primary.name,
                    self._timeout,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "AI-провайдер '%s' дал сбой (%s) — fallback",
                    self._primary.name,
                    exc,
                )

        analysis = await self._fallback.analyze(payload)
        logger.info("Применён rule-based fallback анализа")
        return analysis
