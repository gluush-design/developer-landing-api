"""POST /api/contact — приём обращения с формы обратной связи."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.core.rate_limiter import FileRateLimiter
from app.dependencies import get_contact_service, get_metrics_repo, get_rate_limiter
from app.repositories.metrics_repo import MetricsRepository
from app.schemas.common import ErrorResponse
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.contact_service import ContactService

router = APIRouter(prefix="/api", tags=["contact"])


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить обращение через форму обратной связи",
    responses={
        201: {"description": "Обращение принято и обработано"},
        422: {"model": ErrorResponse, "description": "Ошибка валидации или спам"},
        429: {"model": ErrorResponse, "description": "Превышен лимит запросов"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка"},
    },
)
async def create_contact(
    request: Request,
    payload: ContactRequest,
    service: ContactService = Depends(get_contact_service),
    rate_limiter: FileRateLimiter = Depends(get_rate_limiter),
    metrics: MetricsRepository = Depends(get_metrics_repo),
) -> ContactResponse:
    """Полный цикл: валидация → AI-анализ → письма → сохранение → ответ.

    Защита: rate limiting по IP + honeypot-поле (в схеме) + AI-фильтр спама.
    """
    client_ip = getattr(request.state, "client_ip", "unknown")
    try:
        await rate_limiter.check(client_ip)
    except Exception:
        # Учитываем срабатывание лимита в метриках и пробрасываем дальше.
        await metrics.record_event("rate_limited")
        raise

    return await service.handle(payload, request.state.request_id)
