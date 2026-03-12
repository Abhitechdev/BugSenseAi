"""API router for analysis history."""

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import get_settings
from app.db.session import get_db
from app.models.models import ErrorAnalysis
from app.models.schemas import HistoryResponse, AnalysisRecord
from app.rate_limit import limiter

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["History"])
settings = get_settings()


@router.get("/history", response_model=HistoryResponse)
@limiter.limit(f"{settings.history_rate_limit_per_minute}/minute")
async def get_history(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    input_type: str = Query(None, description="Filter by type: error, log, issue, code"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated analysis history."""
    query = select(ErrorAnalysis).order_by(ErrorAnalysis.created_at.desc())
    count_query = select(func.count(ErrorAnalysis.id))

    if input_type:
        query = query.where(ErrorAnalysis.input_type == input_type)
        count_query = count_query.where(ErrorAnalysis.input_type == input_type)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    analyses = result.scalars().all()

    items = [
        AnalysisRecord(
            id=str(a.id),
            input_type=a.input_type,
            input_text=a.input_text[:500],  # Truncate for listing
            analysis_result=a.analysis_result,
            language_detected=a.language_detected,
            created_at=a.created_at,
        )
        for a in analyses
    ]

    return HistoryResponse(items=items, total=total, page=page, per_page=per_page)

@router.delete("/history/all")
@limiter.limit(f"{settings.history_mutation_rate_limit_per_minute}/minute")
async def delete_all_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete all analysis records from history."""
    from sqlalchemy import delete
    
    # 1. Delete from PostgreSQL
    await db.execute(delete(ErrorAnalysis))
    await db.commit()
    
    # 2. Delete from ChromaDB
    from app.services.vector_service import vector_service
    await vector_service.clear_all()
    
    # 3. Flush Redis Cache
    from app.services.cache_service import cache_service
    await cache_service.clear_all()
    
    logger.info("all_history_cleared")
    return {"message": "All history records deleted successfully"}

@router.delete("/history/category/{category}")
@limiter.limit(f"{settings.history_mutation_rate_limit_per_minute}/minute")
async def delete_category_history(
    request: Request,
    category: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete all analysis records for a specific category."""
    from fastapi import HTTPException
    from sqlalchemy import delete
    from app.services.vector_service import vector_service
    from app.services.cache_service import cache_service

    # Map category to input_type
    category_map = {
        "runtime": "error",
        "cicd": "log",
        "github": "issue",
        "codefix": "code"
    }

    input_type = category_map.get(category)
    if not input_type:
        raise HTTPException(status_code=400, detail="Invalid category")

    # 1. Get all IDs to delete from Vector DB
    query = select(ErrorAnalysis.id).where(ErrorAnalysis.input_type == input_type)
    result = await db.execute(query)
    analysis_ids = [str(id) for id in result.scalars().all()]

    if not analysis_ids:
         return {"message": f"No history found for category {category}"}

    # 2. Delete from Vector DB
    await vector_service.delete_analyses(analysis_ids)
    
    # 3. Clear Cache
    await cache_service.clear_category(input_type)

    # 4. Delete from Postgres
    await db.execute(delete(ErrorAnalysis).where(ErrorAnalysis.input_type == input_type))
    await db.commit()

    logger.info("category_history_cleared", category=category, count=len(analysis_ids))
    return {"message": f"History for {category} deleted successfully"}

@router.delete("/history/{analysis_id}")
@limiter.limit(f"{settings.history_mutation_rate_limit_per_minute}/minute")
async def delete_history(
    request: Request,
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an analysis record from history."""
    from fastapi import HTTPException
    
    query = select(ErrorAnalysis).where(ErrorAnalysis.id == analysis_id)
    result = await db.execute(query)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis record not found")

    await db.delete(analysis)
    await db.commit()
    
    from app.services.vector_service import vector_service
    await vector_service.delete_analysis(analysis_id)
    
    return {"message": "Record deleted successfully"}
