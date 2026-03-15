"""Health check endpoints for external dependencies."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_db
from app.services.ai_service import ai_service
from app.services.cache_service import cache_service
from app.services.turnstile_service import turnstile_service
from app.services.vector_service import vector_service

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Health"])
settings = get_settings()


class HealthStatus:
    """Health status constants."""
    OK = "ok"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class HealthCheck:
    """Individual health check result."""
    def __init__(self, name: str, status: str, message: str = "", details: dict = None):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}


@router.get("/health/db")
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """Check database connectivity and basic operations."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        await db.commit()
        
        return {
            "status": HealthStatus.OK,
            "message": "Database connection successful",
            "details": {
                "connection_test": "passed",
                "read_write": "ok"
            }
        }
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": HealthStatus.CRITICAL,
                "message": "Database connection failed",
                "error": str(e)
            }
        )


@router.get("/health/cache")
async def check_cache_health():
    """Check Redis cache connectivity."""
    try:
        # Test cache connection
        await cache_service.ping()
        
        return {
            "status": HealthStatus.OK,
            "message": "Cache connection successful",
            "details": {
                "connection_test": "passed"
            }
        }
    except Exception as e:
        logger.error("cache_health_check_failed", error=str(e))
        return {
            "status": HealthStatus.DEGRADED,
            "message": "Cache connection failed - AI responses may be slower",
            "error": str(e)
        }


@router.get("/health/vector")
async def check_vector_db_health():
    """Check ChromaDB vector database connectivity."""
    try:
        # Test vector database connection
        await vector_service.ping()
        
        return {
            "status": HealthStatus.OK,
            "message": "Vector database connection successful",
            "details": {
                "connection_test": "passed"
            }
        }
    except Exception as e:
        logger.error("vector_db_health_check_failed", error=str(e))
        return {
            "status": HealthStatus.DEGRADED,
            "message": "Vector database connection failed - similar error search disabled",
            "error": str(e)
        }


@router.get("/health/ai")
async def check_ai_provider_health():
    """Check AI provider connectivity and readiness."""
    try:
        # Test AI provider connection
        await ai_service.ping()
        
        return {
            "status": HealthStatus.OK,
            "message": "AI provider ready",
            "details": {
                "provider": settings.ai_provider,
                "model": settings.ai_model
            }
        }
    except Exception as e:
        logger.error("ai_provider_health_check_failed", error=str(e))
        return {
            "status": HealthStatus.CRITICAL,
            "message": "AI provider unavailable - analysis endpoints will fail",
            "error": str(e),
            "provider": settings.ai_provider
        }


@router.get("/health/turnstile")
async def check_turnstile_health():
    """Check Cloudflare Turnstile service."""
    try:
        if not settings.turnstile_enabled:
            return {
                "status": HealthStatus.OK,
                "message": "Turnstile disabled",
                "details": {
                    "enabled": False
                }
            }
        
        # Test Turnstile service
        await turnstile_service.ping()
        
        return {
            "status": HealthStatus.OK,
            "message": "Turnstile service ready",
            "details": {
                "enabled": True
            }
        }
    except Exception as e:
        logger.error("turnstile_health_check_failed", error=str(e))
        return {
            "status": HealthStatus.DEGRADED,
            "message": "Turnstile service unavailable - spam protection disabled",
            "error": str(e)
        }


@router.get("/health/dependencies")
async def check_all_dependencies():
    """Comprehensive health check for all external dependencies."""
    checks = []
    
    # Database check
    try:
        async with get_db() as db:
            result = await db.execute(text("SELECT 1"))
            await db.commit()
            checks.append(HealthCheck("database", HealthStatus.OK, "Database connection successful"))
    except Exception as e:
        checks.append(HealthCheck("database", HealthStatus.CRITICAL, f"Database connection failed: {str(e)}"))
    
    # Cache check
    try:
        await cache_service.ping()
        checks.append(HealthCheck("cache", HealthStatus.OK, "Cache connection successful"))
    except Exception as e:
        checks.append(HealthCheck("cache", HealthStatus.DEGRADED, f"Cache connection failed: {str(e)}"))
    
    # Vector DB check
    try:
        await vector_service.ping()
        checks.append(HealthCheck("vector_db", HealthStatus.OK, "Vector database connection successful"))
    except Exception as e:
        checks.append(HealthCheck("vector_db", HealthStatus.DEGRADED, f"Vector database connection failed: {str(e)}"))
    
    # AI provider check
    try:
        await ai_service.ping()
        checks.append(HealthCheck("ai_provider", HealthStatus.OK, "AI provider ready"))
    except Exception as e:
        checks.append(HealthCheck("ai_provider", HealthStatus.CRITICAL, f"AI provider unavailable: {str(e)}"))
    
    # Turnstile check
    try:
        if not settings.turnstile_enabled:
            checks.append(HealthCheck("turnstile", HealthStatus.OK, "Turnstile disabled"))
        else:
            await turnstile_service.ping()
            checks.append(HealthCheck("turnstile", HealthStatus.OK, "Turnstile service ready"))
    except Exception as e:
        checks.append(HealthCheck("turnstile", HealthStatus.DEGRADED, f"Turnstile service unavailable: {str(e)}"))
    
    # Determine overall status
    critical_checks = [c for c in checks if c.status == HealthStatus.CRITICAL]
    degraded_checks = [c for c in checks if c.status == HealthStatus.DEGRADED]
    
    if critical_checks:
        overall_status = HealthStatus.CRITICAL
        message = f"Critical issues detected: {len(critical_checks)} service(s) unavailable"
    elif degraded_checks:
        overall_status = HealthStatus.DEGRADED
        message = f"Degraded performance: {len(degraded_checks)} service(s) experiencing issues"
    else:
        overall_status = HealthStatus.OK
        message = "All services healthy"
    
    return {
        "status": overall_status,
        "message": message,
        "timestamp": "2026-03-12T14:21:00Z",  # Would be dynamic in real implementation
        "checks": [
            {
                "name": check.name,
                "status": check.status,
                "message": check.message,
                "details": check.details
            }
            for check in checks
        ]
    }


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "bugsense-ai",
        "version": "1.0.0",
        "timestamp": "2026-03-12T14:21:00Z"  # Would be dynamic in real implementation
    }