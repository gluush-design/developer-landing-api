"""Контракт AI-провайдера и общий системный промпт.

Абстракция позволяет менять провайдера (OpenAI / Anthropic / fallback)
без изменений в бизнес-логике (паттерн Strategy).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

from app.schemas.contact import (
    AIAnalysis,
    ContactRequest,
    Priority,
    RequestCategory,
    Sentiment,
)

# Единый промпт для всех LLM-провайдеров — модель возвращает строго JSON.
SYSTEM_PROMPT = (
    "Ты — ассистент входящих обращений с лендинга backend-разработчика. "
    "Проанализируй обращение и верни СТРОГО валидный JSON без пояснений и markdown.\n"
    "Поля:\n"
    '  "sentiment": один из ["positive","neutral","negative"];\n'
    '  "sentiment_score": число от -1.0 (резкий негатив) до 1.0 (явный позитив);\n'
    '  "category": один из ["collaboration","hiring","project_inquiry",'
    '"support","spam","other"];\n'
    '  "priority": один из ["low","normal","high"];\n'
    '  "summary": краткое резюме обращения на русском (1-2 предложения);\n'
    '  "suggested_reply": вежливый черновик ответа пользователю на русском, '
    "от первого лица разработчика, 2-4 предложения.\n"
    "Отвечай только JSON-объектом."
)


def build_user_prompt(payload: ContactRequest) -> str:
    """Сформировать пользовательскую часть промпта из обращения."""
    return (
        f"Имя: {payload.name}\n"
        f"Email: {payload.email}\n"
        f"Телефон: {payload.phone}\n"
        f"Сообщение: {payload.comment}"
    )


def parse_analysis(raw: str, provider: str) -> AIAnalysis:
    """Распарсить JSON-ответ модели в строго типизированный AIAnalysis.

    Терпимо относится к обёрткам ```json ... ``` и валидирует enum-поля.
    Бросает ValueError при неустранимых проблемах — выше включится fallback.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("В ответе модели нет JSON-объекта")
    data = json.loads(text[start : end + 1])

    return AIAnalysis(
        sentiment=Sentiment(data["sentiment"]),
        sentiment_score=max(-1.0, min(1.0, float(data["sentiment_score"]))),
        category=RequestCategory(data["category"]),
        priority=Priority(data["priority"]),
        summary=str(data["summary"]).strip(),
        suggested_reply=str(data["suggested_reply"]).strip(),
        provider=provider,
    )


class AIProvider(ABC):
    """Интерфейс провайдера AI-анализа."""

    name: str = "base"

    @abstractmethod
    async def analyze(self, payload: ContactRequest) -> AIAnalysis:
        """Проанализировать обращение, вернуть AIAnalysis или бросить исключение."""
        raise NotImplementedError
