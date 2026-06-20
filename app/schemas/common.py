"""Общие схемы: ошибки, health, metrics."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Деталь ошибки валидации (поле -> причина)."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Единый формат тела ошибки для всех 4xx/5xx."""

    success: bool = False
    error: str = Field(..., description="Машиночитаемый код ошибки")
    message: str = Field(..., description="Человекочитаемое описание")
    request_id: str
    details: list[ErrorDetail] | None = None


class DependencyStatus(BaseModel):
    ai: str = Field(..., description="configured | fallback")
    smtp: str = Field(..., description="configured | dry-run")
    storage: str = Field(..., description="ok | error")


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    env: str
    uptime_seconds: float
    dependencies: DependencyStatus


class MetricsResponse(BaseModel):
    """Агрегированная статистика обращений (GET /api/metrics)."""

    total_submissions: int = 0
    by_sentiment: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    ai_analyzed: int = 0
    fallback_used: int = 0
    emails_sent: int = 0
    spam_blocked: int = 0
    rate_limited: int = 0
    avg_processing_ms: float = 0.0
    last_submission_at: str | None = None
