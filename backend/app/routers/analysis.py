"""API router for error, log, issue analysis and code fix endpoints."""

import asyncio
import uuid
import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
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
from app.rate_limit import limiter
from app.services.turnstile_service import turnstile_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["Analysis"])
settings = get_settings()


async def _safe_store_analysis(input_text: str, result: dict, analysis_id: str) -> None:
    try:
        await vector_service.store_analysis(input_text, result, analysis_id)
    except Exception as exc:
        logger.warning("vector_store_background_failed", error=str(exc), analysis_id=analysis_id)


async def _safe_cache_result(input_type: str, input_text: str, result: dict) -> None:
    try:
        await cache_service.set_cached(input_type, input_text, result)
    except Exception as exc:
        logger.warning("cache_store_background_failed", error=str(exc), input_type=input_type)


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

    similar_task = asyncio.create_task(vector_service.search_similar(input_text))

    result = await analysis_func(input_text, **kwargs)
    lang = result.get("language", "unknown")

    similar = []
    try:
        similar = await asyncio.wait_for(similar_task, timeout=0.1)
    except asyncio.TimeoutError:
        similar_task.cancel()
        logger.info("vector_search_deferred", input_type=input_type)
    except Exception as exc:
        logger.warning("vector_search_failed", input_type=input_type, error=str(exc))
    result["similar_errors_found"] = len(similar)

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

    asyncio.create_task(_safe_store_analysis(input_text, result, analysis_id))
    asyncio.create_task(_safe_cache_result(input_type, input_text, result))

    logger.info("analysis_complete", input_type=input_type, analysis_id=analysis_id)
    return AnalysisResponse(**result)


@router.post("/analyze-error", response_model=AnalysisResponse)
@limiter.limit(f"{settings.analysis_rate_limit_per_minute}/minute")
async def analyze_error(request: Request, payload: AnalyzeErrorRequest, db: AsyncSession = Depends(get_db)):
    """Analyze a stack trace or error message."""
    await turnstile_service.verify(payload.turnstile_token, request)
    return await _run_pipeline(
        input_text=payload.input_text,
        input_type="error",
        analysis_func=ai_service.analyze_error,
        db=db,
        language_hint=payload.language_hint,
    )


@router.post("/analyze-log", response_model=AnalysisResponse)
@limiter.limit(f"{settings.analysis_rate_limit_per_minute}/minute")
async def analyze_log(request: Request, payload: AnalyzeLogRequest, db: AsyncSession = Depends(get_db)):
    """Analyze CI/CD build logs."""
    await turnstile_service.verify(payload.turnstile_token, request)
    return await _run_pipeline(
        input_text=payload.input_text,
        input_type="log",
        analysis_func=ai_service.analyze_log,
        db=db,
        ci_platform=payload.ci_platform,
    )


@router.post("/analyze-issue", response_model=AnalysisResponse)
@limiter.limit(f"{settings.analysis_rate_limit_per_minute}/minute")
async def analyze_issue(request: Request, payload: AnalyzeIssueRequest, db: AsyncSession = Depends(get_db)):
    """Analyze a GitHub issue."""
    await turnstile_service.verify(payload.turnstile_token, request)
    return await _run_pipeline(
        input_text=payload.input_text,
        input_type="issue",
        analysis_func=ai_service.analyze_issue,
        db=db,
        repo_url=payload.repo_url,
    )


@router.post("/fix-code", response_model=AnalysisResponse)
@limiter.limit(f"{settings.analysis_rate_limit_per_minute}/minute")
async def fix_code(request: Request, payload: CodeFixRequest, db: AsyncSession = Depends(get_db)):
    """Generate a fix for buggy code."""
    await turnstile_service.verify(payload.turnstile_token, request)
    return await _run_pipeline(
        input_text=payload.buggy_code,
        input_type="code",
        analysis_func=ai_service.fix_code,
        db=db,
        error_message=payload.error_message,
        language=payload.language,
    )
