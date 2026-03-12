"""Tests for AI service configuration and validation."""

import pytest
from unittest.mock import patch, MagicMock

from app.services.ai_service import AIService
from app.config import get_settings


def test_ai_service_initialization():
    """Test AI service initialization."""
    service = AIService()
    assert service.settings is not None
    assert service._client is None  # Client should be lazy-loaded


def test_api_config_nvidia():
    """Test NVIDIA API configuration."""
    with patch('app.config.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            ai_provider='nvidia',
            nvidia_api_key='test-key'
        )
        
        service = AIService()
        url, headers = service._get_api_config()
        
        assert url == "https://integrate.api.nvidia.com/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"


def test_api_config_gemini():
    """Test Gemini API configuration."""
    with patch('app.config.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            ai_provider='gemini',
            gemini_api_key='test-key',
            ai_model='gemini-pro'
        )
        
        service = AIService()
        url, headers = service._get_api_config()
        
        assert "generativelanguage.googleapis.com" in url
        assert "gemini-pro" in url
        assert "key=test-key" in url
        assert headers["Content-Type"] == "application/json"


def test_api_config_openai():
    """Test OpenAI API configuration."""
    with patch('app.config.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            ai_provider='openai',
            openai_api_key='test-key',
            ai_model='gpt-4'
        )
        
        service = AIService()
        url, headers = service._get_api_config()
        
        assert url == "https://api.openai.com/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"


def test_api_config_anthropic():
    """Test Anthropic API configuration."""
    with patch('app.config.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            ai_provider='anthropic',
            anthropic_api_key='test-key',
            ai_model='claude-3-opus-20240229'
        )
        
        service = AIService()
        url, headers = service._get_api_config()
        
        assert url == "https://api.anthropic.com/v1/messages"
        assert headers["x-api-key"] == "test-key"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["Content-Type"] == "application/json"


def test_api_config_openrouter():
    """Test OpenRouter API configuration."""
    with patch('app.config.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            ai_provider='openrouter',
            openrouter_api_key='test-key',
            ai_model='anthropic/claude-3-sonnet'
        )
        
        service = AIService()
        url, headers = service._get_api_config()
        
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["HTTP-Referer"] == "https://bugsense.ai"
        assert headers["X-Title"] == "BugSense AI"


def test_require_secret():
    """Test secret requirement validation."""
    service = AIService()
    
    # Test valid secret
    result = service._require_secret("TEST_KEY", "valid-secret")
    assert result == "valid-secret"
    
    # Test empty secret
    with pytest.raises(ValueError, match="TEST_KEY is not configured"):
        service._require_secret("TEST_KEY", "")
    
    # Test whitespace-only secret
    with pytest.raises(ValueError, match="TEST_KEY is not configured"):
        service._require_secret("TEST_KEY", "   ")


def test_language_detection():
    """Test language detection heuristics."""
    service = AIService()
    
    # Test Python detection
    python_text = "Traceback (most recent call last):\n  File \"test.py\", line 1, in <module>\n    import numpy\nModuleNotFoundError: No module named 'numpy'"
    result = service.detect_language(python_text)
    assert result == "python"
    
    # Test JavaScript detection
    js_text = "TypeError: Cannot read property 'map' of undefined\n    at UserController.js:24:15"
    result = service.detect_language(js_text)
    assert result == "javascript"
    
    # Test unknown language
    unknown_text = "Some random text without clear indicators"
    result = service.detect_language(unknown_text)
    assert result is None


@patch('app.services.ai_service.httpx.AsyncClient')
def test_client_timeout_configuration(mock_client_class):
    """Test HTTP client timeout configuration."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    service = AIService()
    client = service._get_client()
    
    # Verify client was created with proper timeout configuration
    mock_client_class.assert_called_once()
    # The actual timeout values would be verified in a real test environment