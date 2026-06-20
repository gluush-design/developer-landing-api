"""Общие фикстуры тестов.

Каждый тест получает изолированное файловое хранилище (tmp_path) и
приложение без реального AI/SMTP — значит, детерминированно работает
rule-based fallback и dry-run почта.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        app_env="local",
        ai_provider="none",
        openai_api_key=None,
        anthropic_api_key=None,
        smtp_host=None,
        data_dir=tmp_path / "data",
        rate_limit_max_requests=5,
        rate_limit_window_seconds=600,
        cors_allow_origins="*",
    )


@pytest.fixture
def client(settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_payload() -> dict:
    return {
        "name": "Иван Петров",
        "email": "ivan@example.com",
        "phone": "+7 999 123-45-67",
        "comment": "Здравствуйте! Хочу заказать разработку backend API для проекта.",
        "website": "",
    }
