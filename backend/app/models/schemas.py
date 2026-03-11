"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import bleach


class AnalyzeRequest(BaseModel):
    """Base request for all analysis endpoints."""
    input_text: str = Field(..., min_length=10, max_length=50000, description="The error/log/issue text to analyze")

    @field_validator("input_text")
    @classmethod
    def sanitize_input(cls, v: str) -> str:
        return bleach.clean(v, tags=[], strip=True)


class AnalyzeErrorRequest(AnalyzeRequest):
    """Request body for error analysis."""
    language_hint: Optional[str] = Field(None, max_length=50, description="Optional language hint (python, javascript, etc.)")


class AnalyzeLogRequest(AnalyzeRequest):
    """Request body for CI/CD log analysis."""
    ci_platform: Optional[str] = Field(None, max_length=50, description="CI platform (github_actions, gitlab_ci, jenkins, etc.)")


class AnalyzeIssueRequest(AnalyzeRequest):
    """Request body for GitHub issue analysis."""
    repo_url: Optional[str] = Field(None, max_length=500, description="Optional repository URL for context")


class CodeFixRequest(BaseModel):
    """Request body for code fix generation."""
    buggy_code: str = Field(..., min_length=5, max_length=50000, description="The buggy code to fix")
    error_message: Optional[str] = Field(None, max_length=5000, description="Optional error message")
    language: Optional[str] = Field(None, max_length=50, description="Programming language")

    @field_validator("buggy_code")
    @classmethod
    def sanitize_code(cls, v: str) -> str:
        return bleach.clean(v, tags=[], strip=True)


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
