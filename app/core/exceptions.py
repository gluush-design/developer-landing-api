"""Доменные исключения приложения.

Каждое несёт HTTP-статус и машиночитаемый код — глобальный обработчик
превращает их в единый формат `ErrorResponse`.
"""
from __future__ import annotations


class AppError(Exception):
    """Базовое доменное исключение."""

    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "Внутренняя ошибка сервиса"

    def __init__(self, message: str | None = None) -> None:
        if message:
            self.message = message
        super().__init__(self.message)


class RateLimitExceeded(AppError):
    status_code = 429
    error_code = "rate_limit_exceeded"
    message = "Слишком много запросов. Попробуйте позже."

    def __init__(self, retry_after: int, message: str | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


class SpamDetected(AppError):
    status_code = 422
    error_code = "spam_detected"
    message = "Обращение отклонено как спам."


class StorageError(AppError):
    status_code = 500
    error_code = "storage_error"
    message = "Ошибка сохранения данных."
