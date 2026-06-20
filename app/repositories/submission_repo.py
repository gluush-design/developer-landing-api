"""Репозиторий обращений — append-only хранилище в формате JSONL.

Каждая заявка — одна строка JSON. Формат удобно стримить и грепать;
не требует БД (по ТЗ хранилище может быть файловым).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.exceptions import StorageError
from app.schemas.contact import AIAnalysis, ContactRequest

logger = logging.getLogger("app.repo.submission")


class SubmissionRepository:
    """Хранение принятых обращений (JSON Lines)."""

    def __init__(self, storage_file: Path) -> None:
        self._file = storage_file
        self._lock = asyncio.Lock()

    async def save(self, payload: ContactRequest, analysis: AIAnalysis) -> dict:
        """Сохранить обращение, вернуть сохранённую запись (с id и временем)."""
        record = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": payload.name,
            "phone": payload.phone,
            "email": str(payload.email),
            "comment": payload.comment,
            "analysis": analysis.model_dump(),
        }
        line = json.dumps(record, ensure_ascii=False)
        try:
            async with self._lock:
                self._file.parent.mkdir(parents=True, exist_ok=True)
                with self._file.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        except OSError as exc:
            logger.error("Не удалось сохранить обращение: %s", exc)
            raise StorageError() from exc
        return record

    async def count(self) -> int:
        """Количество обращений (для health/диагностики)."""
        if not self._file.exists():
            return 0
        async with self._lock:
            with self._file.open("r", encoding="utf-8") as fh:
                return sum(1 for line in fh if line.strip())
