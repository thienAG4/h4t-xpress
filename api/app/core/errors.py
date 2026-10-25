"""Business errors and the single JSON error shape: {"error": {code, message, details}}.

Services raise AppError subclasses with a stable `code`; the web app maps codes to
user-facing text, so messages here are short English hints for API consumers.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(
        self, message: str, *, code: str | None = None, details: Any | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class TooManyRequests(AppError):
    status_code = 429
    code = "TOO_MANY_REQUESTS"


def _error_body(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def error_response(exc: AppError) -> JSONResponse:
    """Build the error response directly, for endpoints that must also alter headers."""
    return JSONResponse(
        _error_body(exc.code, exc.message, exc.details), status_code=exc.status_code
    )


# =============================== Handlers ===============================


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        _error_body(exc.code, exc.message, exc.details), status_code=exc.status_code
    )


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Keep only what a client needs to highlight the right field.
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        _error_body("VALIDATION_ERROR", "Request data is invalid", details), status_code=422
    )


async def _handle_http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return JSONResponse(
        _error_body(code.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)),
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("[unhandled] %s %s failed: %s", request.method, request.url.path, exc)
    return JSONResponse(
        _error_body("INTERNAL_ERROR", "Something went wrong, please try again"), status_code=500
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
