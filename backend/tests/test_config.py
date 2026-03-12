"""Tests for configuration loading and validation."""

import os
import pytest
from app.config import get_settings, Settings


def test_config_loading():
    """Test that configuration loads without errors."""
    settings = get_settings()
    assert settings.app_name == "BugSense AI"
    assert settings.app_env in ["development", "production"]
    assert settings.debug is not None
    assert settings.secret_key


def test_database_url_normalization():
    """Test that database URLs are normalized correctly."""
    # Test with various URL formats
    test_urls = [
        "postgresql://user:pass@localhost:5432/db",
        "postgresql+psycopg2://user:pass@localhost:5432/db",
        "postgresql+asyncpg://user:pass@localhost:5432/db",
    ]
    
    for url in test_urls:
        settings = Settings(database_url=url)
        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert "user:pass@localhost:5432/db" in settings.database_url


def test_ai_provider_validation():
    """Test AI provider configuration validation."""
    valid_providers = ["nvidia", "gemini", "openai", "anthropic", "openrouter"]
    
    for provider in valid_providers:
        settings = Settings(ai_provider=provider)
        assert settings.ai_provider == provider
    
    # Test invalid provider
    with pytest.raises(ValueError):
        Settings(ai_provider="invalid")


def test_cors_configuration():
    """Test CORS configuration parsing."""
    settings = Settings(cors_origins="http://localhost:3000,https://example.com")
    assert "http://localhost:3000" in settings.cors_origin_list
    assert "https://example.com" in settings.cors_origin_list


def test_trusted_hosts_configuration():
    """Test trusted hosts configuration parsing."""
    settings = Settings(trusted_hosts="localhost,127.0.0.1,*.example.com")
    assert "localhost" in settings.trusted_host_list
    assert "127.0.0.1" in settings.trusted_host_list
    assert "*.example.com" in settings.trusted_host_list


def test_production_mode_detection():
    """Test production mode detection."""
    settings = Settings(app_env="production")
    assert settings.is_production is True
    
    settings = Settings(app_env="development")
    assert settings.is_production is False


def test_turnstile_configuration():
    """Test Turnstile configuration."""
    settings = Settings(turnstile_secret_key="test-key")
    assert settings.turnstile_enabled is True
    
    settings = Settings(turnstile_secret_key="")
    assert settings.turnstile_enabled is False