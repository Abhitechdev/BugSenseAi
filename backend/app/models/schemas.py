"""Pydantic schemas for request/response validation."""

from datetime import datetime
import re
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_INPUT_LENGTHS = {
    "error": 20000,
    "log": 40000,
    "issue": 25000,
    "code": 30000,
    "error_message": 3000,
}

MAX_LINE_COUNTS = {
    "error": 1200,
    "log": 2000,
    "issue": 1000,
    "code": 1500,
    "error_message": 200,
}

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{199,}")
BASE64_BLOB_PATTERN = re.compile(r"(?:data:[^,\s]+;base64,)?[A-Za-z0-9+/]{512,}={0,2}")
HEX_BLOB_PATTERN = re.compile(r"\b[a-fA-F0-9]{512,}\b")
URL_PATTERN = re.compile(r"https?://\S+")


def _normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _validate_text_payload(value: str, kind: str) -> str:
    if not value:
        raise ValueError("Input cannot be empty after sanitization.")
    if CONTROL_CHAR_PATTERN.search(value):
        raise ValueError("Input contains unsupported control characters.")
    if len(value) > MAX_INPUT_LENGTHS[kind]:
        raise ValueError(f"{kind.title()} input exceeds {MAX_INPUT_LENGTHS[kind]} characters.")

    line_count = value.count("\n") + 1
    if line_count > MAX_LINE_COUNTS[kind]:
        raise ValueError(f"{kind.title()} input exceeds {MAX_LINE_COUNTS[kind]} lines.")

    if len(URL_PATTERN.findall(value)) > 100:
        raise ValueError("Input contains too many URLs and looks like scraped or spam content.")
    if REPEATED_CHAR_PATTERN.search(value):
        raise ValueError("Input appears to contain repeated spam content.")
    if BASE64_BLOB_PATTERN.search(value) or HEX_BLOB_PATTERN.search(value):
        raise ValueError("Input appears to contain a large encoded or binary blob. Submit only the relevant excerpt.")

    technical_chars = sum(char.isalnum() for char in value)
    if technical_chars < 10:
        raise ValueError("Input must contain meaningful technical content.")
    return value


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if isinstance(value, str):
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        return normalized or None
    return value


class AnalyzeRequest(BaseModel):
    """Base request for all analysis endpoints."""
    input_text: str = Field(..., min_length=10, max_length=50000, description="The error/log/issue text to analyze")
    turnstile_token: Optional[str] = Field(None, max_length=2048, description="Cloudflare Turnstile token")

    @field_validator("input_text")
    @classmethod
    def sanitize_input(cls, v: str) -> str:
        return _normalize_text(v)

    @field_validator("turnstile_token")
    @classmethod
    def sanitize_turnstile_token(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v


class AnalyzeErrorRequest(AnalyzeRequest):
    """Request body for error analysis."""
    language_hint: Optional[str] = Field(None, max_length=50, description="Optional language hint (python, javascript, etc.)")

    @field_validator("language_hint")
    @classmethod
    def sanitize_language_hint(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(v)

    @model_validator(mode="after")
    def validate_error_input(self):
        self.input_text = _validate_text_payload(self.input_text, "error")
        return self


class AnalyzeLogRequest(AnalyzeRequest):
    """Request body for CI/CD log analysis."""
    ci_platform: Optional[str] = Field(None, max_length=50, description="CI platform (github_actions, gitlab_ci, jenkins, etc.)")

    @field_validator("ci_platform")
    @classmethod
    def sanitize_ci_platform(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(v)

    @model_validator(mode="after")
    def validate_log_input(self):
        self.input_text = _validate_text_payload(self.input_text, "log")
        return self


class AnalyzeIssueRequest(AnalyzeRequest):
    """Request body for GitHub issue analysis."""
    repo_url: Optional[str] = Field(None, max_length=500, description="Optional repository URL for context")

    @field_validator("repo_url")
    @classmethod
    def sanitize_repo_url(cls, v: Optional[str]) -> Optional[str]:
        normalized = _normalize_optional_text(v)
        if not normalized:
            return None
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("repo_url must be a valid http or https URL.")
        return normalized

    @model_validator(mode="after")
    def validate_issue_input(self):
        self.input_text = _validate_text_payload(self.input_text, "issue")
        return self


class CodeFixRequest(BaseModel):
    """Request body for code fix generation."""
    buggy_code: str = Field(..., min_length=5, max_length=50000, description="The buggy code to fix")
    error_message: Optional[str] = Field(None, max_length=5000, description="Optional error message")
    language: Optional[str] = Field(None, max_length=50, description="Programming language")
    turnstile_token: Optional[str] = Field(None, max_length=2048, description="Cloudflare Turnstile token")

    @field_validator("buggy_code")
    @classmethod
    def sanitize_code(cls, v: str) -> str:
        return _normalize_text(v)

    @field_validator("error_message", "language")
    @classmethod
    def sanitize_code_metadata(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(v)

    @field_validator("turnstile_token")
    @classmethod
    def sanitize_code_turnstile_token(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_code_input(self):
        self.buggy_code = _validate_text_payload(self.buggy_code, "code")
        if self.error_message:
            self.error_message = _validate_text_payload(self.error_message, "error_message")
        return self


class AnalysisResponse(BaseModel):
    """Structured response from analysis."""
    language: str
    environment: str
    error_type: str
    explanation: str
    root_cause: str
    fix: str
    example_solution: str
    similar_errors_found: int = 0


class AnalysisRecord(BaseModel):
    """A single history record."""
    id: str
    input_type: str
    input_text: str
    analysis_result: dict
    language_detected: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    """Paginated history response."""
    items: list[AnalysisRecord]
    total: int
    page: int
    per_page: int
