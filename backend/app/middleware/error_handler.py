"""Error handling middleware for consistent API responses."""

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

logger = structlog.get_logger(__name__)


def _unwrap_retry_error(exc: Exception) -> Exception:
    """Unwrap tenacity RetryError to get the real cause."""
    try:
        from tenacity import RetryError
        if isinstance(exc, RetryError):
            return exc.last_attempt.exception() or exc
    except ImportError:
        pass
    return exc


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns structured error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as raw_exc:
            exc = _unwrap_retry_error(raw_exc)

            # AI API returned an HTTP error (401, 400, 429, etc.)
            if isinstance(exc, httpx.HTTPStatusError):
                detail = f"AI API error (HTTP {exc.response.status_code})"
                try:
                    body = exc.response.json()
                    if isinstance(body.get("error"), dict):
                        detail = body["error"].get("message", detail)
                    elif "message" in body:
                        detail = body["message"]
                except Exception:
                    pass
                logger.error("ai_api_error", path=request.url.path, status=exc.response.status_code, detail=detail)
                return JSONResponse(
                    status_code=502,
                    content={"error": "AI Service Error", "detail": detail},
                )

            # Can't reach AI API
            if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
                logger.error("connection_error", path=request.url.path, error=str(exc))
                return JSONResponse(
                    status_code=503,
                    content={"error": "Connection Error", "detail": "Could not connect to the AI service. Please check your network and try again."},
                )

            # Validation errors
            if isinstance(exc, ValueError):
                logger.warning("validation_error", path=request.url.path, error=str(exc))
                return JSONResponse(
                    status_code=422,
                    content={"error": "Validation Error", "detail": str(exc)},
                )

            # Everything else
            logger.error(
                "unhandled_error",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error", "detail": str(exc)},
            )
