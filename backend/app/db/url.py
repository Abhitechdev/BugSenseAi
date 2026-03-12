"""Database URL helpers for async SQLAlchemy and asyncpg."""


ASYNC_DRIVER_PREFIX = "postgresql+asyncpg://"
RAW_POSTGRES_PREFIX = "postgresql://"

_POSTGRES_PREFIXES = (
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "postgresql+psycopg2://",
    "postgresql://",
    "postgres://",
)


def _replace_postgres_prefix(url: str, replacement: str) -> str:
    normalized = url.strip()
    for prefix in _POSTGRES_PREFIXES:
        if normalized.startswith(prefix):
            return f"{replacement}{normalized[len(prefix):]}"
    return normalized


def normalize_async_database_url(url: str) -> str:
    """Force Postgres URLs onto the asyncpg driver for AsyncEngine usage."""
    return _replace_postgres_prefix(url, ASYNC_DRIVER_PREFIX)


def normalize_asyncpg_connect_url(url: str) -> str:
    """Convert SQLAlchemy-style Postgres URLs into a DSN asyncpg can consume."""
    return _replace_postgres_prefix(url, RAW_POSTGRES_PREFIX)
