"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError


logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    application = FastAPI(
        title="Doc Q&A Portal API",
        version=__version__,
        description="Plain-text ingestion and retrieval-augmented question answering.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.include_router(router)

    if settings is not None:
        application.dependency_overrides[get_settings] = lambda: resolved_settings

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        logger.exception("Application request failed: %s", exc)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.public_message, "code": exc.code},
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unexpected application error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "The request could not be completed.",
                "code": "internal_error",
            },
        )

    return application


app = create_app()
