"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.models.schemas import ErrorDetail, ErrorResponse


logger = logging.getLogger(__name__)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(by_alias=True),
        headers=headers,
    )


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

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.info("Request validation failed with %d issue(s).", len(exc.errors()))
        return _error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Invalid request payload.",
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        if exc.status_code >= 500:
            code = "INTERNAL_ERROR"
            message = "An unexpected server error occurred."
        else:
            code = "INVALID_REQUEST"
            message = exc.detail if isinstance(exc.detail, str) else "Invalid request."
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            headers=exc.headers,
        )

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        logger.exception("Application request failed: %s", exc)
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.public_message,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unexpected application error: %s", exc)
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
        )

    return application


app = create_app()
