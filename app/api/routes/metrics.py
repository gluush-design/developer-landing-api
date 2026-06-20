"""GET /api/metrics — агрегированная статистика обращений."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_metrics_repo
from app.repositories.metrics_repo import MetricsRepository
from app.schemas.common import MetricsResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/metrics", response_model=MetricsResponse, summary="Статистика обращений")
async def metrics(repo: MetricsRepository = Depends(get_metrics_repo)) -> MetricsResponse:
    return await repo.get()
