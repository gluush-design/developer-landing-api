"""Конфигурация приложения.

Все настройки читаются из переменных окружения / `.env` через pydantic-settings.
Один источник правды для конфига — экземпляр `Settings`, отдаётся через
кэшированный `get_settings()` (удобно подменять в тестах).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Типобезопасные настройки сервиса."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Приложение ---
    app_name: str = "Developer Landing API"
    app_env: Literal["local", "production"] = "local"
    app_debug: bool = True
    app_version: str = "1.0.0"

    cors_allow_origins: str = "*"

    # --- AI ---
    ai_provider: Literal["openai", "anthropic", "none"] = "openai"
    ai_timeout_seconds: float = 12.0

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"

    # --- Почта ---
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    mail_from: str = "no-reply@example.com"
    mail_from_name: str = "Developer Landing"
    owner_email: str = "owner@example.com"

    # --- Rate limiting ---
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 600

    # --- Хранилище ---
    data_dir: Path = Field(default=Path("./data"))
    log_level: str = "INFO"

    @field_validator("data_dir", mode="before")
    @classmethod
    def _expand_data_dir(cls, value: str | Path) -> Path:
        return Path(value).expanduser()

    # ----- Производные свойства -----

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS-origin'ы в виде списка."""
        raw = self.cors_allow_origins.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def submissions_file(self) -> Path:
        return self.data_dir / "submissions.jsonl"

    @property
    def metrics_file(self) -> Path:
        return self.data_dir / "metrics.json"

    @property
    def ratelimit_file(self) -> Path:
        return self.data_dir / "ratelimit.json"

    @property
    def ai_enabled(self) -> bool:
        """Сконфигурирован ли реальный AI-провайдер (есть провайдер и ключ)."""
        if self.ai_provider == "openai":
            return bool(self.openai_api_key)
        if self.ai_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False

    @property
    def smtp_enabled(self) -> bool:
        """Сконфигурирован ли реальный SMTP (иначе dry-run в лог)."""
        return bool(self.smtp_host)

    def ensure_dirs(self) -> None:
        """Создать каталоги под данные/логи, если их ещё нет."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Кэшированный синглтон настроек."""
    return Settings()
