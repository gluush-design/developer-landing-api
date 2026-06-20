"""Тесты rule-based AI fallback (анализ без внешнего провайдера)."""
from __future__ import annotations

import asyncio

import pytest

from app.schemas.contact import ContactRequest, RequestCategory, Sentiment
from app.services.ai.fallback_provider import FallbackProvider


def _analyze(comment: str) -> "object":
    provider = FallbackProvider()
    payload = ContactRequest(
        name="Тест Тестов",
        email="test@example.com",
        phone="+7 999 000-00-00",
        comment=comment,
    )
    return asyncio.run(provider.analyze(payload))


def test_fallback_detects_positive_sentiment():
    result = _analyze("Спасибо, отличный сайт, очень нравится ваш подход!")
    assert result.sentiment == Sentiment.POSITIVE
    assert result.sentiment_score > 0
    assert result.provider == "fallback"


def test_fallback_detects_negative_sentiment():
    result = _analyze("Это ужасно, ничего не работает и всё очень медленно.")
    assert result.sentiment == Sentiment.NEGATIVE
    assert result.sentiment_score < 0


def test_fallback_classifies_project_inquiry():
    result = _analyze("Хочу заказать разработку backend и API для проекта.")
    assert result.category == RequestCategory.PROJECT_INQUIRY


def test_fallback_classifies_hiring():
    result = _analyze("У нас открыта вакансия, ищем разработчика на позицию fulltime.")
    assert result.category == RequestCategory.HIRING


def test_fallback_detects_spam():
    result = _analyze(
        "Заработок крипта! Инвестиции http://bit.ly/x и https://casino.example промокод"
    )
    assert result.category == RequestCategory.SPAM


def test_fallback_reply_addresses_user_by_name():
    result = _analyze("Здравствуйте, хочу обсудить сотрудничество и партнёрство.")
    assert "Тест" in result.suggested_reply


@pytest.mark.parametrize("comment", ["Нейтральное сообщение без эмоций про погоду сегодня."])
def test_fallback_neutral(comment):
    result = _analyze(comment)
    assert result.sentiment == Sentiment.NEUTRAL
    assert result.sentiment_score == 0.0
