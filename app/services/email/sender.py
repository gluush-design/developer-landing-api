"""Отправка email по SMTP (async) с dry-run fallback.

Если SMTP не сконфигурирован — письмо не теряется, а логируется (dry-run).
Сбой отправки не роняет бизнес-операцию: метод возвращает bool.
"""
from __future__ import annotations

import logging
from email.message import EmailMessage as MimeMessage

from app.config import Settings
from app.services.email.templates import EmailMessage

logger = logging.getLogger("app.email")


class EmailSender:
    """Адаптер отправки писем."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _build_mime(self, message: EmailMessage) -> MimeMessage:
        mime = MimeMessage()
        mime["From"] = f"{self._settings.mail_from_name} <{self._settings.mail_from}>"
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text_body)
        mime.add_alternative(message.html_body, subtype="html")
        return mime

    async def send(self, message: EmailMessage) -> bool:
        """Отправить письмо. Возвращает True при успехе/dry-run, False при ошибке."""
        if not self._settings.smtp_enabled:
            logger.info(
                "[DRY-RUN] Письмо не отправлено (SMTP не настроен). "
                "to=%s subject=%r",
                message.to,
                message.subject,
            )
            return True  # в dry-run считаем «доставленным» для метрик/UX

        try:
            import aiosmtplib

            await aiosmtplib.send(
                self._build_mime(message),
                hostname=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_username,
                password=self._settings.smtp_password,
                start_tls=self._settings.smtp_use_tls,
                timeout=15,
            )
            logger.info("Письмо отправлено: to=%s subject=%r", message.to, message.subject)
            return True
        except Exception as exc:  # noqa: BLE001 — почта не должна ронять запрос
            logger.error("Ошибка отправки письма на %s: %s", message.to, exc)
            return False
