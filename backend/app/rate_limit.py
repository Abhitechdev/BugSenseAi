"""Shared rate-limiting configuration."""

from fastapi import Request
from slowapi import Limiter

from app.config import get_settings

settings = get_settings()


def get_rate_limit_key(request: Request) -> str:
    """Prefer real client IP headers when running behind proxies."""
    forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)
