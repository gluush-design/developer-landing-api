"""Схемы формы обратной связи и результата AI-анализа."""
from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator

# Телефон: международный формат, 7–15 цифр, опциональный "+", разделители.
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,20}$")
# Сколько цифр должно остаться после очистки.
_PHONE_DIGITS = re.compile(r"\d")


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RequestCategory(str, Enum):
    """Тип обращения (классификация)."""

    COLLABORATION = "collaboration"   # предложение о сотрудничестве
    HIRING = "hiring"                 # вакансия / наём
    PROJECT_INQUIRY = "project_inquiry"  # заказ проекта
    SUPPORT = "support"               # вопрос / поддержка
    SPAM = "spam"                     # спам
    OTHER = "other"                   # прочее


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ContactRequest(BaseModel):
    """Входные данные формы обратной связи (POST /api/contact)."""

    name: str = Field(..., min_length=2, max_length=100, examples=["Иван Петров"])
    phone: str = Field(..., min_length=7, max_length=25, examples=["+7 999 123-45-67"])
    email: EmailStr = Field(..., examples=["ivan@example.com"])
    comment: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        examples=["Здравствуйте! Хотим обсудить разработку backend для нашего стартапа."],
    )
    # Honeypot: скрытое поле, которое заполняют только боты. Люди оставляют пустым.
    website: str | None = Field(default=None, max_length=0, examples=[""])

    @field_validator("name", "comment")
    @classmethod
    def _strip_and_collapse(cls, value: str) -> str:
        """Тримминг и схлопывание повторяющихся пробелов (санитизация)."""
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            raise ValueError("Поле не может состоять только из пробелов")
        return cleaned

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        value = value.strip()
        if not _PHONE_RE.match(value):
            raise ValueError("Некорректный номер телефона")
        if len(_PHONE_DIGITS.findall(value)) < 7:
            raise ValueError("В номере телефона должно быть минимум 7 цифр")
        return value


class AIAnalysis(BaseModel):
    """Результат AI-обработки обращения (или fallback)."""

    sentiment: Sentiment
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="-1 негатив … +1 позитив")
    category: RequestCategory
    priority: Priority
    summary: str = Field(..., description="Краткое резюме обращения (1–2 предложения)")
    suggested_reply: str = Field(..., description="Черновик ответа пользователю")
    provider: str = Field(..., description="Кто выполнил анализ: openai | anthropic | fallback")


class ContactResponse(BaseModel):
    """Ответ на успешно принятое обращение."""

    success: bool = True
    request_id: str
    message: str = "Обращение принято. Мы свяжемся с вами в ближайшее время."
    submission_id: str
    analysis: AIAnalysis
    email_owner_sent: bool
    email_user_sent: bool
    processing_ms: int
