"""Redis caching service for BugSense AI."""

import json
import hashlib
import structlog
from typing import Optional
import redis.asyncio as redis
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CacheService:
    """Redis-backed caching for analysis results."""

    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> Optional[redis.Redis]:
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._client.ping()
                logger.info("redis_connected")
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e))
                self._client = None
        return self._client

    def _make_key(self, prefix: str, text: str) -> str:
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"bugsense:{prefix}:{text_hash}"

    async def get_cached(self, prefix: str, input_text: str) -> Optional[dict]:
        """Retrieve cached analysis result."""
        client = await self._get_client()
        if client is None:
            return None

        key = self._make_key(prefix, input_text)
        try:
            cached = await client.get(key)
            if cached:
                logger.info("cache_hit", key=key)
                return json.loads(cached)
        except Exception as e:
            logger.error("cache_get_error", error=str(e))
        return None

    async def set_cached(self, prefix: str, input_text: str, result: dict, ttl: int = DEFAULT_TTL) -> None:
        """Store analysis result in cache."""
        client = await self._get_client()
        if client is None:
            return

        key = self._make_key(prefix, input_text)
        try:
            await client.setex(key, ttl, json.dumps(result))
            logger.info("cache_set", key=key, ttl=ttl)
        except Exception as e:
            logger.error("cache_set_error", error=str(e))

    async def close(self):
        if self._client:
            await self._client.close()

    async def clear_category(self, input_type: str) -> None:
        """Clear cached results for a specific category."""
        client = await self._get_client()
        if client is None:
            return

        try:
            pattern = f"bugsense:{input_type}:*"
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
            logger.info("cache_category_cleared", category=input_type, keys_deleted=len(keys))
        except Exception as e:
            logger.error("cache_category_clear_failed", category=input_type, error=str(e))

    async def clear_all(self) -> None:
        """Clear all stored analysis cache."""
        client = await self._get_client()
        if client is None:
            return
        
        try:
            await client.flushdb()
            logger.info("cache_cleared")
        except Exception as e:
            logger.error("cache_clear_failed", error=str(e))


# Singleton
cache_service = CacheService()
