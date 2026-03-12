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
    cors_origins: str = "http://localhost:3000,http://frontend:3000"
    cors_origin_regex: str = r"https://.*\.up\.railway\.app"

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

    class Config:
        env_file = (".env.local", ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
