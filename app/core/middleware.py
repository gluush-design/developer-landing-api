"""HTTP-middleware: request_id, тайминг и логирование каждого запроса в файл."""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import request_id_ctx

logger = logging.getLogger("app.request")


def client_ip(request: Request) -> str:
    """Достаём IP клиента с учётом обратного прокси (X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Присваивает request_id, замеряет длительность, логирует запрос/ответ."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id
        request.state.client_ip = client_ip(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "%s %s -> %s (%dms)",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                extra={
                    "extra": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": request.state.client_ip,
                    }
                },
            )
            # Прокидываем request_id в ответ — удобно для отладки на фронте.
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id
            request_id_ctx.reset(token)
