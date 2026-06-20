"""Глобальные обработчики ошибок — единый формат ответа `ErrorResponse`.

Покрывают: доменные AppError, ошибки валидации (422) и любые
непойманные исключения (500). Ни один стектрейс не утекает клиенту.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, RateLimitExceeded
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("app.error")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _json(payload: ErrorResponse, status_code: int, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Подключить обработчики к приложению."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = None
        if isinstance(exc, RateLimitExceeded):
            headers = {"Retry-After": str(exc.retry_after)}
        logger.warning("AppError %s: %s", exc.error_code, exc.message)
        return _json(
            ErrorResponse(
                error=exc.error_code,
                message=exc.message,
                request_id=_request_id(request),
            ),
            exc.status_code,
            headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            ErrorDetail(
                field=".".join(str(p) for p in err["loc"] if p != "body"),
                message=err["msg"],
            )
            for err in exc.errors()
        ]
        logger.info("Ошибка валидации: %s", details)
        return _json(
            ErrorResponse(
                error="validation_error",
                message="Некорректные входные данные.",
                request_id=_request_id(request),
                details=details,
            ),
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _json(
            ErrorResponse(
                error="http_error",
                message=str(exc.detail),
                request_id=_request_id(request),
            ),
            exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Логируем со стектрейсом, наружу отдаём только request_id.
        logger.exception("Непойманное исключение: %s", exc)
        return _json(
            ErrorResponse(
                error="internal_error",
                message="Внутренняя ошибка сервиса. Сообщите request_id в поддержку.",
                request_id=_request_id(request),
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
