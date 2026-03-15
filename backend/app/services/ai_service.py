"""AI Analysis Service — core LLM integration for BugSense AI."""

import json
import httpx
import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()
