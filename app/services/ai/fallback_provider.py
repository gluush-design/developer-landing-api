"""Rule-based fallback анализа — работает БЕЗ внешнего AI.

Гарантирует, что полный цикл обращения завершается даже если LLM недоступен,
нет ключа или превышен таймаут. Простая, но осмысленная эвристика:
лексиконы тональности + ключевые слова категорий.
"""
from __future__ import annotations

import re

from app.schemas.contact import (
    AIAnalysis,
    ContactRequest,
    Priority,
    RequestCategory,
    Sentiment,
)
from app.services.ai.base import AIProvider

_POSITIVE = {
    "спасибо", "отлично", "круто", "супер", "нравится", "восхищ", "класс",
    "благодар", "рад", "интересн", "впечатл", "great", "thanks", "awesome",
    "love", "cool", "excellent",
}
_NEGATIVE = {
    "плохо", "ужас", "ужасн", "разочаров", "недоволен", "отврат", "жаль",
    "проблем", "не работает", "ошибк", "медленн", "дорого", "bad", "terrible",
    "awful", "hate", "broken", "slow", "expensive", "scam",
}

_CATEGORY_KEYWORDS: list[tuple[RequestCategory, tuple[str, ...]]] = [
    (RequestCategory.HIRING, ("ваканс", "наём", "найм", "ставк", "оффер", "hr",
                              "позици", "fulltime", "зарплат", "job", "hiring")),
    (RequestCategory.PROJECT_INQUIRY, ("проект", "разработ", "сайт", "лендинг",
                                       "приложен", "бэкенд", "backend", "api",
                                       "интеграц", "заказ", "бюджет", "смет",
                                       "техзадан", "тз")),
    (RequestCategory.COLLABORATION, ("сотруднич", "партн", "коллаборац",
                                     "совместн", "collab", "partnership")),
    (RequestCategory.SUPPORT, ("вопрос", "помог", "поддержк", "консультац",
                               "как ", "не работает", "помощь", "support",
                               "help", "question")),
]

_SPAM_MARKERS = (
    "http://", "https://", "www.", "viagra", "casino", "крипт", "инвестиц",
    "заработок", "млн", "розыгрыш", "промокод", "telegram.me", "bit.ly",
)
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


class FallbackProvider(AIProvider):
    """Детерминированный анализ на правилах (без сети)."""

    name = "fallback"

    async def analyze(self, payload: ContactRequest) -> AIAnalysis:
        text = payload.comment.lower()

        sentiment, score = self._sentiment(text)
        category = self._category(text)
        priority = self._priority(category, sentiment)
        summary = self._summary(payload)
        reply = self._reply(payload, category)

        return AIAnalysis(
            sentiment=sentiment,
            sentiment_score=score,
            category=category,
            priority=priority,
            summary=summary,
            suggested_reply=reply,
            provider=self.name,
        )

    @staticmethod
    def _sentiment(text: str) -> tuple[Sentiment, float]:
        pos = sum(1 for w in _POSITIVE if w in text)
        neg = sum(1 for w in _NEGATIVE if w in text)
        if pos == neg:
            return Sentiment.NEUTRAL, 0.0
        total = pos + neg
        score = round((pos - neg) / total, 2)
        if score > 0:
            return Sentiment.POSITIVE, score
        return Sentiment.NEGATIVE, score

    @staticmethod
    def _category(text: str) -> RequestCategory:
        spam_hits = sum(1 for marker in _SPAM_MARKERS if marker in text)
        if spam_hits >= 2 or (spam_hits >= 1 and len(_URL_RE.findall(text)) >= 2):
            return RequestCategory.SPAM
        for category, keywords in _CATEGORY_KEYWORDS:
            if any(kw in text for kw in keywords):
                return category
        return RequestCategory.OTHER

    @staticmethod
    def _priority(category: RequestCategory, sentiment: Sentiment) -> Priority:
        if category in (RequestCategory.PROJECT_INQUIRY, RequestCategory.HIRING):
            return Priority.HIGH
        if category == RequestCategory.SPAM:
            return Priority.LOW
        if sentiment == Sentiment.NEGATIVE:
            return Priority.HIGH
        return Priority.NORMAL

    @staticmethod
    def _summary(payload: ContactRequest) -> str:
        snippet = payload.comment[:160]
        if len(payload.comment) > 160:
            snippet += "…"
        return f"Обращение от {payload.name}: {snippet}"

    @staticmethod
    def _reply(payload: ContactRequest, category: RequestCategory) -> str:
        first_name = payload.name.split()[0]
        intro = f"Здравствуйте, {first_name}! Спасибо за обращение."
        tail = {
            RequestCategory.PROJECT_INQUIRY: (
                " Я изучу детали проекта и вернусь с оценкой и вопросами в "
                "ближайшее время."
            ),
            RequestCategory.HIRING: (
                " Спасибо за интерес к сотрудничеству — отвечу по вакансии в "
                "ближайшее время."
            ),
            RequestCategory.COLLABORATION: (
                " Идея сотрудничества интересна, давайте обсудим детали."
            ),
            RequestCategory.SUPPORT: (
                " Уточню детали по вашему вопросу и подготовлю ответ."
            ),
            RequestCategory.SPAM: " Спасибо за сообщение.",
            RequestCategory.OTHER: " Я свяжусь с вами в ближайшее время.",
        }[category]
        return intro + tail
