"""BugSense AI — FastAPI application entry point."""

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging_config import setup_logging
from app.routers import analysis, history
from app.services.ai_service import ai_service
from app.services.cache_service import cache_service

settings = get_settings()
setup_logging(debug=settings.debug)
logger = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("bugsense_starting", env=settings.app_env)
    yield
    logger.info("bugsense_shutting_down")
    await ai_service.close()
    await cache_service.close()


app = FastAPI(
    title=settings.app_name,
    description="AI-powered developer tool that explains software errors and suggests fixes.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex_value,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(analysis.router)
app.include_router(history.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": settings.app_name, "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "env": settings.app_env}
