"""Request audit logging middleware with sensitive data filtering."""

from __future__ import annotations

import hashlib
import time
import uuid
import re
from typing import Any, Dict, Optional

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.rate_limit import get_rate_limit_key

logger = structlog.get_logger(__name__)
settings = get_settings()

# Patterns to detect sensitive data that should be filtered from logs
SENSITIVE_PATTERNS = {
    "api_keys": re.compile(r"(?i)(api[_-]?key|apikey|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9\-_]{20,})['\"]?"),
    "passwords": re.compile(r"(?i)(password|pwd|pass)\s*[:=]\s*['\"]?([^&'\"]{3,})['\"]?"),
    "tokens": re.compile(r"(?i)(bearer|token|authorization)\s+['\"]?([a-zA-Z0-9\-_\.]{20,})['\"]?"),
    "emails": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "credit_cards": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"),
    "crypto_addresses": re.compile(r"\b(?:0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "phone_numbers": re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
    "ip_addresses": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one structured access log entry per request without logging sensitive payload fragments."""

    @staticmethod
    def _hash_client(value: str) -> str:
        salted = f"{settings.secret_key}:{value}".encode("utf-8")
        return hashlib.sha256(salted).hexdigest()[:16]

    @staticmethod
    def _filter_sensitive_data(data: Any) -> Any:
        """Recursively filter sensitive data from request/response data."""
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                # Skip known sensitive keys entirely
                if key.lower() in {'password', 'pwd', 'pass', 'api_key', 'apikey', 'access_token', 'auth_token', 'bearer', 'token', 'authorization'}:
                    filtered[key] = "[FILTERED]"
                else:
                    filtered[key] = AuditLoggingMiddleware._filter_sensitive_data(value)
            return filtered
        elif isinstance(data, list):
            return [AuditLoggingMiddleware._filter_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            # Apply regex patterns to filter sensitive strings
            filtered = data
            for pattern_name, pattern in SENSITIVE_PATTERNS.items():
                if pattern_name == "api_keys":
                    filtered = pattern.sub(r'\1: "[FILTERED_API_KEY]"', filtered)
                elif pattern_name == "passwords":
                    filtered = pattern.sub(r'\1: "[FILTERED_PASSWORD]"', filtered)
                elif pattern_name == "tokens":
                    filtered = pattern.sub(r'\1 "[FILTERED_TOKEN]"', filtered)
                else:
                    # For other patterns, replace with pattern name
                    filtered = pattern.sub(f"[{pattern_name.upper()}_FILTERED]", filtered)
            return filtered
        else:
            return data

    @staticmethod
    def _sanitize_query_params(query_string: str) -> str:
        """Sanitize query parameters to remove sensitive data."""
        if not query_string:
            return ""
        
        # Split into key-value pairs
        pairs = query_string.split('&')
        sanitized_pairs = []
        
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                # Check if this is a sensitive parameter
                if key.lower() in {'password', 'pwd', 'pass', 'api_key', 'apikey', 'access_token', 'auth_token', 'bearer', 'token', 'authorization'}:
                    sanitized_pairs.append(f"{key}=[FILTERED]")
                else:
                    sanitized_pairs.append(pair)
            else:
                sanitized_pairs.append(pair)
        
        return '&'.join(sanitized_pairs)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        client_ip = get_rate_limit_key(request)
        client_hash = self._hash_client(client_ip)
        start = time.perf_counter()

        request.state.request_id = request_id
        request.state.client_hash = client_hash
        
        # Extract and sanitize query parameters
        query_string = str(request.query_params)
        sanitized_query = self._sanitize_query_params(query_string)
        
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_hash=client_hash,
            method=request.method,
            path=request.url.path,
            query_params=sanitized_query[:500] if sanitized_query else None,  # Limit length
        )

        # Log request details (without sensitive data)
        request_details = {
            "method": request.method,
            "path": request.url.path,
            "query_params": sanitized_query[:500] if sanitized_query else None,
            "content_type": request.headers.get("content-type", ""),
            "user_agent": request.headers.get("user-agent", "")[:200] if request.headers.get("user-agent") else "",  # Limit length
        }

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers.setdefault("X-Request-ID", request_id)

            logger.info(
                "http_request",
                status_code=response.status_code,
                duration_ms=duration_ms,
                route=request.url.path,
                request_details=self._filter_sensitive_data(request_details),
            )
            return response
        except Exception as e:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            
            # Filter sensitive data from exception details
            exception_details = {
                "exception_type": type(e).__name__,
                "exception_message": str(e)[:500] if str(e) else "",  # Limit length
            }
            
            logger.exception(
                "http_request_failed",
                duration_ms=duration_ms,
                route=request.url.path,
                exception_details=self._filter_sensitive_data(exception_details),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
