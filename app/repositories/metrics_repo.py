"""Репозиторий метрик — агрегированная статистика в одном JSON-файле.

Инкрементально обновляется на каждое значимое событие. Чтение — для
GET /api/metrics. Запись атомарна (через временный файл + replace).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.common import MetricsResponse
from app.schemas.contact import AIAnalysis

logger = logging.getLogger("app.repo.metrics")


def _empty_metrics() -> dict:
    return MetricsResponse().model_dump()


class MetricsRepository:
    """Хранение и инкрементальное обновление агрегированных метрик."""

    def __init__(self, storage_file: Path) -> None:
        self._file = storage_file
        self._lock = asyncio.Lock()

    def _read_unsafe(self) -> dict:
        if not self._file.exists():
            return _empty_metrics()
        try:
            with self._file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            base = _empty_metrics()
            base.update({k: v for k, v in data.items() if k in base})
            return base
        except (json.JSONDecodeError, OSError):
            return _empty_metrics()

    def _write_unsafe(self, data: dict) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(self._file)

    @staticmethod
    def _bump(counter: dict[str, int], key: str) -> None:
        counter[key] = counter.get(key, 0) + 1

    async def record_submission(
        self,
        analysis: AIAnalysis,
        *,
        processing_ms: int,
        emails_sent: int,
    ) -> None:
        """Учесть успешно принятое обращение."""
        async with self._lock:
            m = self._read_unsafe()
            total = m["total_submissions"] + 1
            m["total_submissions"] = total

            self._bump(m["by_sentiment"], analysis.sentiment.value)
            self._bump(m["by_category"], analysis.category.value)
            self._bump(m["by_priority"], analysis.priority.value)

            if analysis.provider == "fallback":
                m["fallback_used"] += 1
            else:
                m["ai_analyzed"] += 1

            m["emails_sent"] += emails_sent

            # Скользящее среднее времени обработки.
            prev_avg = m["avg_processing_ms"]
            m["avg_processing_ms"] = round(
                prev_avg + (processing_ms - prev_avg) / total, 2
            )
            m["last_submission_at"] = datetime.now(timezone.utc).isoformat()
            self._write_unsafe(m)

    async def record_event(self, event: str) -> None:
        """Учесть служебное событие: spam_blocked | rate_limited."""
        async with self._lock:
            m = self._read_unsafe()
            if event in m and isinstance(m[event], int):
                m[event] += 1
                self._write_unsafe(m)

    async def get(self) -> MetricsResponse:
        async with self._lock:
            return MetricsResponse(**self._read_unsafe())
