"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
from pydantic import field_validator
from app.db.url import normalize_async_database_url


class Settings(BaseSettings):
    # ── App ──
    app_name: str = "BugSense AI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    trusted_hosts: str = "localhost,127.0.0.1,backend,*.railway.app,*.railway.internal"
    max_request_body_bytes: int = 262144
    cors_origins: str = "http://localhost:3000,http://frontend:3000"
    cors_origin_regex: str = r"https://.*\.up\.railway\.app"
    turnstile_secret_key: str = ""
    turnstile_allowed_hostnames: str = "localhost,127.0.0.1,*.up.railway.app"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://bugsense:bugsense_secret@postgres:5432/bugsense_db"

    # ── Redis ──
    redis_url: str = "redis://redis:6379/0"

    # ── AI ──
    ai_provider: str = "nvidia"   # nvidia | gemini | openai | openrouter | anthropic
    nvidia_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    ai_model: str = "meta/llama-3.3-70b-instruct"

    # ── ChromaDB ──
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    # ── Rate Limiting ──
    rate_limit_per_minute: int = 30
    analysis_rate_limit_per_minute: int = 10
    history_rate_limit_per_minute: int = 30
    history_mutation_rate_limit_per_minute: int = 5
    health_rate_limit_per_minute: int = 120

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return value

    @field_validator("ai_provider", mode="before")
    @classmethod
    def normalize_ai_provider(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if isinstance(value, str):
            return normalize_async_database_url(value)
        return value

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex_value(self) -> str | None:
        normalized = self.cors_origin_regex.strip()
        return normalized or None

    @property
    def trusted_host_list(self) -> List[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def turnstile_allowed_hostname_list(self) -> List[str]:
        return [host.strip() for host in self.turnstile_allowed_hostnames.split(",") if host.strip()]

    @property
    def turnstile_enabled(self) -> bool:
        return bool(self.turnstile_secret_key.strip())

    class Config:
        env_file = (".env.local", ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
