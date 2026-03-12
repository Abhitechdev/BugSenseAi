"""Cloudflare Turnstile server-side verification."""

from fnmatch import fnmatch
from typing import Optional

import httpx
import structlog
from fastapi import Request

from app.config import get_settings

logger = structlog.get_logger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileService:
    """Validates Turnstile tokens against Cloudflare's Siteverify API."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    def _hostname_allowed(self, hostname: str | None) -> bool:
        if not hostname:
            return True
        return any(fnmatch(hostname, pattern) for pattern in self.settings.turnstile_allowed_hostname_list)

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return None

    async def verify(self, token: str | None, request: Request, expected_action: str = "analysis") -> None:
        if not self.settings.turnstile_enabled:
            return

        cleaned_token = (token or "").strip()
        if not cleaned_token:
            raise ValueError("Security challenge is required.")

        client = await self._get_client()
        payload = {
            "secret": self.settings.turnstile_secret_key,
            "response": cleaned_token,
        }
        client_ip = self._get_client_ip(request)
        if client_ip:
            payload["remoteip"] = client_ip

        response = await client.post(SITEVERIFY_URL, data=payload)
        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            logger.warning(
                "turnstile_failed",
                error_codes=result.get("error-codes", []),
                hostname=result.get("hostname"),
            )
            raise ValueError("Security challenge verification failed. Please retry.")

        hostname = result.get("hostname")
        if not self._hostname_allowed(hostname):
            logger.warning("turnstile_invalid_hostname", hostname=hostname)
            raise ValueError("Security challenge hostname is not allowed.")

        action = result.get("action")
        if action and action != expected_action:
            logger.warning("turnstile_action_mismatch", expected=expected_action, actual=action)
            raise ValueError("Security challenge action mismatch.")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


turnstile_service = TurnstileService()
