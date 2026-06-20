"""Точка сборки FastAPI-приложения (application factory).

Подключает: конфиг, логирование, DI-контейнер (lifespan), CORS, middleware
с request_id и логированием, глобальные обработчики ошибок, роуты API,
Swagger/OpenAPI (из коробки) и статический фронтенд-лендинг.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.routes import contact, health, metrics
from app.config import Settings, get_settings
from app.core.middleware import RequestContextMiddleware
from app.dependencies import build_container
from app.logging_config import configure_logging

logger = logging.getLogger("app")

STATIC_DIR = Path(__file__).parent / "static"

OPENAPI_DESCRIPTION = """
Бэкенд-сервис лендинга разработчика.

**Возможности**
* `POST /api/contact` — приём обращения: валидация → AI-анализ → письма → ответ
* `GET /api/health` — статус сервиса и зависимостей
* `GET /api/metrics` — агрегированная статистика обращений

AI-функции: анализ тональности, классификация типа обращения и генерация
черновика ответа. При недоступности AI работает rule-based fallback.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл: сборка контейнера на старте."""
    settings: Settings = app.state.settings
    app.state.container = build_container(settings)
    app.state.started_at = time.time()
    logger.info(
        "Сервис запущен: env=%s ai=%s smtp=%s",
        settings.app_env,
        "configured" if settings.ai_enabled else "fallback",
        "configured" if settings.smtp_enabled else "dry-run",
    )
    yield
    logger.info("Сервис остановлен")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Создать и сконфигурировать приложение."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=OPENAPI_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_origins_list != ["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # request_id + логирование запросов.
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(contact.router)
    app.include_router(health.router)
    app.include_router(metrics.router)

    # Фронтенд-лендинг.
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")
    else:

        @app.get("/", include_in_schema=False)
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/docs")

    return app


# Экземпляр для uvicorn: `uvicorn app.main:app`
app = create_app()
