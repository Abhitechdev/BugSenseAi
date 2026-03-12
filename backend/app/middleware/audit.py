"""Request audit logging middleware."""

from __future__ import annotations

import hashlib
import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.rate_limit import get_rate_limit_key

logger = structlog.get_logger(__name__)
settings = get_settings()


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured access log entry per request without logging payloads."""

    @staticmethod
    def _hash_client(value: str) -> str:
        salted = f"{settings.secret_key}:{value}".encode("utf-8")
        return hashlib.sha256(salted).hexdigest()[:16]

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        client_ip = get_rate_limit_key(request)
        client_hash = self._hash_client(client_ip)
        start = time.perf_counter()

        request.state.request_id = request_id
        request.state.client_hash = client_hash
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_hash=client_hash,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers.setdefault("X-Request-ID", request_id)

            logger.info(
                "http_request",
                status_code=response.status_code,
                duration_ms=duration_ms,
                route=request.url.path,
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "http_request_failed",
                duration_ms=duration_ms,
                route=request.url.path,
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
