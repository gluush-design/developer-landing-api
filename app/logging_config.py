"""Настройка логирования.

Два назначения:
  * консоль — человекочитаемо;
  * файл `data/logs/app.log` — структурированный JSON, с ротацией.

Каждая строка лога несёт `request_id` (если есть в контексте запроса),
что позволяет связать все события одного HTTP-запроса.
"""
from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
from datetime import datetime, timezone

from app.config import Settings

# request_id текущего запроса (проставляется middleware).
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class RequestIdFilter(logging.Filter):
    """Добавляет request_id из contextvar в каждую запись лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Формат JSON-строки на запись лога (по строке на событие)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        # Произвольные поля, переданные через logger.info(..., extra={"extra": {...}})
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    """Сконфигурировать корневой логгер один раз на процесс."""
    settings.ensure_dirs()

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Защита от повторной инициализации (например, при reload в тестах).
    if any(getattr(h, "_app_handler", False) for h in root.handlers):
        return

    request_filter = RequestIdFilter()

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(request_id)s | %(name)s | %(message)s"
        )
    )
    console.addFilter(request_filter)
    console._app_handler = True  # type: ignore[attr-defined]

    file_handler = logging.handlers.RotatingFileHandler(
        settings.logs_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(request_filter)
    file_handler._app_handler = True  # type: ignore[attr-defined]

    root.handlers = [console, file_handler]

    # Приглушаем слишком болтливые сторонние логгеры.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
