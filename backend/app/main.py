"""BugSense AI — FastAPI application entry point."""

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.middleware.audit import AuditLoggingMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging_config import setup_logging
from app.middleware.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.rate_limit import limiter
from app.routers import analysis, history
from app.services.ai_service import ai_service
from app.services.cache_service import cache_service
from app.services.turnstile_service import turnstile_service

settings = get_settings()
setup_logging(debug=settings.debug)
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("bugsense_starting", env=settings.app_env)
    yield
    logger.info("bugsense_shutting_down")
    await ai_service.close()
    await cache_service.close()
    await turnstile_service.close()


app = FastAPI(
    title=settings.app_name,
    description="AI-powered developer tool that explains software errors and suggests fixes.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ── Middleware ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex_value,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLoggingMiddleware)

# ── Routers ──
app.include_router(analysis.router)
app.include_router(history.router)


@app.get("/", tags=["Health"])
@limiter.limit(f"{settings.health_rate_limit_per_minute}/minute")
async def root(request: Request):
    return {"status": "ok"}


@app.get("/health", tags=["Health"])
@limiter.limit(f"{settings.health_rate_limit_per_minute}/minute")
async def health_check(request: Request):
    return {"status": "healthy"}
