"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──
    app_name: str = "BugSense AI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"

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

    class Config:
        env_file = (".env.local", ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
