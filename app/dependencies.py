"""Composition root и FastAPI-зависимости (Dependency Injection).

Все синглтоны (репозитории, сервисы, rate limiter) собираются один раз в
`build_container()` при старте и кладутся в `app.state`. Хэндлеры получают
их через тонкие Depends-функции — это упрощает подмену в тестах.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.config import Settings
from app.core.rate_limiter import FileRateLimiter
from app.repositories.metrics_repo import MetricsRepository
from app.repositories.submission_repo import SubmissionRepository
from app.services.ai.analyzer import AIAnalyzer
from app.services.contact_service import ContactService
from app.services.email.sender import EmailSender


@dataclass
class Container:
    """Контейнер собранных зависимостей приложения."""

    settings: Settings
    rate_limiter: FileRateLimiter
    submissions: SubmissionRepository
    metrics: MetricsRepository
    analyzer: AIAnalyzer
    email_sender: EmailSender
    contact_service: ContactService


def build_container(settings: Settings) -> Container:
    """Собрать граф зависимостей из настроек."""
    settings.ensure_dirs()

    rate_limiter = FileRateLimiter(
        storage_file=settings.ratelimit_file,
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    submissions = SubmissionRepository(settings.submissions_file)
    metrics = MetricsRepository(settings.metrics_file)
    analyzer = AIAnalyzer(settings)
    email_sender = EmailSender(settings)
    contact_service = ContactService(
        analyzer=analyzer,
        email_sender=email_sender,
        submissions=submissions,
        metrics=metrics,
        owner_email=settings.owner_email,
    )
    return Container(
        settings=settings,
        rate_limiter=rate_limiter,
        submissions=submissions,
        metrics=metrics,
        analyzer=analyzer,
        email_sender=email_sender,
        contact_service=contact_service,
    )


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_contact_service(request: Request) -> ContactService:
    return request.app.state.container.contact_service


def get_rate_limiter(request: Request) -> FileRateLimiter:
    return request.app.state.container.rate_limiter


def get_metrics_repo(request: Request) -> MetricsRepository:
    return request.app.state.container.metrics
