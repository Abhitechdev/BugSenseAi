"""API router for error, log, issue analysis and code fix endpoints."""

import uuid
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import ErrorAnalysis
from app.models.schemas import (
    AnalyzeErrorRequest,
    AnalyzeLogRequest,
    AnalyzeIssueRequest,
    CodeFixRequest,
    AnalysisResponse,
)
from app.services.ai_service import ai_service
from app.services.vector_service import vector_service
from app.services.cache_service import cache_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Analysis"])


async def _run_pipeline(
    input_text: str,
    input_type: str,
    analysis_func,
    db: AsyncSession,
    **kwargs,
) -> AnalysisResponse:
    """Shared analysis pipeline: cache check → vector search → LLM → store."""

    # 1. Check cache
    cached = await cache_service.get_cached(input_type, input_text)
    if cached:
        return AnalysisResponse(**cached)

    # 3. Search vector DB for similar errors
    similar = await vector_service.search_similar(input_text)

    # 4. Call LLM
    result = await analysis_func(input_text, **kwargs)
    lang = result.get("language", "unknown")
    result["similar_errors_found"] = len(similar)

    # 5. Store in database
    analysis_id = str(uuid.uuid4())
    db_record = ErrorAnalysis(
        id=analysis_id,
        input_type=input_type,
        input_text=input_text[:10000],
        analysis_result=result,
        language_detected=lang,
    )
    db.add(db_record)
    await db.flush()

    # 6. Store in vector DB & cache (fire-and-forget style)
    await vector_service.store_analysis(input_text, result, analysis_id)
    await cache_service.set_cached(input_type, input_text, result)

    logger.info("analysis_complete", input_type=input_type, analysis_id=analysis_id)
    return AnalysisResponse(**result)


@router.post("/analyze-error", response_model=AnalysisResponse)
async def analyze_error(request: AnalyzeErrorRequest, db: AsyncSession = Depends(get_db)):
    """Analyze a stack trace or error message."""
    return await _run_pipeline(
        input_text=request.input_text,
        input_type="error",
        analysis_func=ai_service.analyze_error,
        db=db,
        language_hint=request.language_hint,
    )


@router.post("/analyze-log", response_model=AnalysisResponse)
async def analyze_log(request: AnalyzeLogRequest, db: AsyncSession = Depends(get_db)):
    """Analyze CI/CD build logs."""
    return await _run_pipeline(
        input_text=request.input_text,
        input_type="log",
        analysis_func=ai_service.analyze_log,
        db=db,
        ci_platform=request.ci_platform,
    )


@router.post("/analyze-issue", response_model=AnalysisResponse)
async def analyze_issue(request: AnalyzeIssueRequest, db: AsyncSession = Depends(get_db)):
    """Analyze a GitHub issue."""
    return await _run_pipeline(
        input_text=request.input_text,
        input_type="issue",
        analysis_func=ai_service.analyze_issue,
        db=db,
        repo_url=request.repo_url,
    )


@router.post("/fix-code", response_model=AnalysisResponse)
async def fix_code(request: CodeFixRequest, db: AsyncSession = Depends(get_db)):
    """Generate a fix for buggy code."""
    return await _run_pipeline(
        input_text=request.buggy_code,
        input_type="code",
        analysis_func=ai_service.fix_code,
        db=db,
        error_message=request.error_message,
        language=request.language,
    )
