"""ContactService — оркестратор полного цикла обработки обращения.

Реализует требование ТЗ: «запрос → валидация → бизнес-логика → AI →
отправка → ответ». Валидация выполняется на уровне Pydantic-схемы (до
сервиса), здесь — бизнес-логика, AI, письма, персистентность, метрики.
"""
from __future__ import annotations

import logging
import time

from app.core.exceptions import SpamDetected
from app.repositories.metrics_repo import MetricsRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.contact import ContactRequest, ContactResponse, RequestCategory
from app.services.ai.analyzer import AIAnalyzer
from app.services.email.sender import EmailSender
from app.services.email.templates import build_owner_email, build_user_email

logger = logging.getLogger("app.service.contact")


class ContactService:
    """Бизнес-логика приёма обращения."""

    def __init__(
        self,
        analyzer: AIAnalyzer,
        email_sender: EmailSender,
        submissions: SubmissionRepository,
        metrics: MetricsRepository,
        owner_email: str,
    ) -> None:
        self._analyzer = analyzer
        self._email = email_sender
        self._submissions = submissions
        self._metrics = metrics
        self._owner_email = owner_email

    async def handle(self, payload: ContactRequest, request_id: str) -> ContactResponse:
        """Полный цикл обработки одного обращения."""
        started = time.perf_counter()

        # 1. Бизнес-логика + AI: анализ тональности, категории, черновик ответа.
        analysis = await self._analyzer.analyze(payload)

        # 2. Отсечение спама по результату анализа (после AI — осознанное решение).
        if analysis.category == RequestCategory.SPAM:
            await self._metrics.record_event("spam_blocked")
            logger.warning("Обращение классифицировано как спам и отклонено")
            raise SpamDetected()

        # 3. Персистентность обращения.
        record = await self._submissions.save(payload, analysis)

        # 4. Отправка писем: владельцу + копия пользователю.
        owner_msg = build_owner_email(self._owner_email, payload, analysis)
        user_msg = build_user_email(payload, analysis)
        owner_sent = await self._email.send(owner_msg)
        user_sent = await self._email.send(user_msg)

        processing_ms = int((time.perf_counter() - started) * 1000)

        # 5. Метрики.
        await self._metrics.record_submission(
            analysis,
            processing_ms=processing_ms,
            emails_sent=int(owner_sent) + int(user_sent),
        )

        logger.info(
            "Обращение обработано: id=%s category=%s sentiment=%s provider=%s",
            record["id"],
            analysis.category.value,
            analysis.sentiment.value,
            analysis.provider,
        )

        # 6. Ответ клиенту.
        return ContactResponse(
            request_id=request_id,
            submission_id=record["id"],
            analysis=analysis,
            email_owner_sent=owner_sent,
            email_user_sent=user_sent,
            processing_ms=processing_ms,
        )
