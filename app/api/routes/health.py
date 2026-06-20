"""GET /api/health — проверка статуса сервиса и его зависимостей."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from app.dependencies import Container, get_container
from app.schemas.common import DependencyStatus, HealthResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Health-check сервиса")
async def health(request: Request, container: Container = Depends(get_container)) -> HealthResponse:
    settings = container.settings
    started_at = getattr(request.app.state, "started_at", time.time())

    # Проверка доступности файлового хранилища.
    try:
        settings.ensure_dirs()
        storage = "ok"
    except OSError:
        storage = "error"

    return HealthResponse(
        app=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
        uptime_seconds=round(time.time() - started_at, 2),
        dependencies=DependencyStatus(
            ai="configured" if settings.ai_enabled else "fallback",
            smtp="configured" if settings.smtp_enabled else "dry-run",
            storage=storage,
        ),
    )
