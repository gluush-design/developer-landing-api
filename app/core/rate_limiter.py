"""Файловый rate limiter (sliding window) — защита от спама.

По требованию ТЗ хранилище — файловое (JSON). Алгоритм «скользящего окна»:
для каждого ключа (IP) держим список таймстемпов запросов в пределах окна.
Доступ к файлу сериализуется через asyncio.Lock (один процесс).
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from app.core.exceptions import RateLimitExceeded


class FileRateLimiter:
    """Ограничитель частоты запросов с персистентностью в JSON-файле."""

    def __init__(self, storage_file: Path, max_requests: int, window_seconds: int) -> None:
        self._file = storage_file
        self._max = max_requests
        self._window = window_seconds
        self._lock = asyncio.Lock()

    def _read(self) -> dict[str, list[float]]:
        if not self._file.exists():
            return {}
        try:
            with self._file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            # Повреждённый файл не должен ронять сервис — начинаем с чистого листа.
            return {}

    def _write(self, data: dict[str, list[float]]) -> None:
        tmp = self._file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)
        tmp.replace(self._file)  # атомарная замена

    async def check(self, key: str) -> None:
        """Учесть запрос от `key`. Бросает RateLimitExceeded при превышении."""
        now = time.time()
        cutoff = now - self._window

        async with self._lock:
            data = self._read()

            # Чистим устаревшие записи по всем ключам (компактим файл).
            for existing_key in list(data.keys()):
                fresh = [ts for ts in data[existing_key] if ts > cutoff]
                if fresh:
                    data[existing_key] = fresh
                else:
                    del data[existing_key]

            timestamps = data.get(key, [])

            if len(timestamps) >= self._max:
                oldest = min(timestamps)
                retry_after = max(1, int(oldest + self._window - now))
                raise RateLimitExceeded(
                    retry_after=retry_after,
                    message=(
                        f"Превышен лимит {self._max} запросов за "
                        f"{self._window} сек. Повторите через {retry_after} сек."
                    ),
                )

            timestamps.append(now)
            data[key] = timestamps
            self._write(data)
