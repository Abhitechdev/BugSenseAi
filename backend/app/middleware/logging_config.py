"""Structured logging configuration using structlog."""

import logging
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import structlog


_STRICT_REDACT_KEYS = {
    "anthropic_api_key",
    "api_key",
    "authorization",
    "cookie",
    "gemini_api_key",
    "nvidia_api_key",
    "openai_api_key",
    "openrouter_api_key",
    "password",
    "secret",
    "secret_key",
    "set-cookie",
    "token",
    "turnstile_secret_key",
    "turnstile_token",
}
_PAYLOAD_SUMMARY_KEYS = {
    "body",
    "detail",
    "error",
    "input_text",
    "prompt",
    "raw_content",
}
_MAX_LOG_STRING_LENGTH = 240
_SECRET_PATTERNS = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE), "Bearer [redacted]"),
    (re.compile(r"\bnvapi-[A-Za-z0-9_\-]+\b"), "nvapi-[redacted]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]+\b"), "sk-[redacted]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"), "AIza[redacted]"),
)
_BLOB_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9+/]{300,}={0,2}\b"),
    re.compile(r"\b[a-fA-F0-9]{300,}\b"),
)


def _redact_secret_patterns(value: str) -> str:
    sanitized = value
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    for pattern in _BLOB_PATTERNS:
        sanitized = pattern.sub("[blob-redacted]", sanitized)
    return sanitized


def _summarize_string(value: str) -> str:
    sanitized = _redact_secret_patterns(value)
    if len(sanitized) <= _MAX_LOG_STRING_LENGTH:
        return sanitized
    return f"{sanitized[:_MAX_LOG_STRING_LENGTH]}... [truncated len={len(sanitized)}]"


def _sanitize_value(key: str | None, value: Any) -> Any:
    normalized_key = (key or "").lower()
    if normalized_key in _STRICT_REDACT_KEYS:
        return "[redacted]"

    if isinstance(value, Mapping):
        return {nested_key: _sanitize_value(str(nested_key), nested_value) for nested_key, nested_value in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(normalized_key, item) for item in value]

    if isinstance(value, str):
        sanitized = _summarize_string(value)
        if normalized_key in _PAYLOAD_SUMMARY_KEYS:
            return f"[omitted len={len(value)} preview={sanitized!r}]"
        return sanitized

    return value


def _sanitize_event_dict(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return {key: _sanitize_value(str(key), value) for key, value in event_dict.items()}


def setup_logging(debug: bool = False):
    """Configure structured logging for the application."""

    log_level = logging.DEBUG if debug else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            _sanitize_event_dict,
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging to go through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
