"""
JobPilot AI — FastAPI Application Entry Point

Application factory pattern with lifespan management.
Includes all module routers.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure parent directory is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from core.config import settings
from core.database import dispose_db, get_engine
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    JobPilotException,
    LLMProviderError,
    NotFoundError,
    ValidationError,
)
from core.logger import get_logger
from core.middleware import RequestLoggingMiddleware
from core.redis_client import close_redis

logger = get_logger(__name__)

APP_VERSION = "1.0.0"


def _init_error_tracking() -> None:
    """Wire Sentry when a DSN is configured.

    SENTRY_DSN was already a setting but nothing consumed it, so production
    errors went nowhere but the container log.
    """
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        logger.info("sentry_initialised", environment=settings.APP_ENV)
    except Exception as e:
        logger.warning("sentry_init_failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────
    logger.info("starting_jobpilot", env=settings.APP_ENV)
    _init_error_tracking()
    engine = get_engine()
    # Auto-create tables in development; production uses Alembic migrations.
    if settings.APP_ENV == "development":
        # Importing the models module is what registers every table on
        # Base.metadata — without it create_all() silently creates nothing.
        from core import models  # noqa: F401
        from core.database import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_ready", tables=len(Base.metadata.tables))

    if settings.DEMO_MODE:
        from core.demo import seed_demo_data

        await seed_demo_data()
    yield
    # ── Shutdown ─────────────────────────────────────────
    logger.info("shutting_down_jobpilot")
    await dispose_db()
    await close_redis()
    logger.info("connections_closed")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="JobPilot AI",
        description="""
        Intelligent career copilot that automates and optimizes job search.

        ## Features
        - Multi-platform job search
        - AI-powered resume matching and ATS scoring
        - Smart cover letter generation
        - Application tracking and analytics
        - Multi-provider LLM abstraction
        """,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ───────────────────────────────
    # Each domain error maps to one status code in exactly one place, so a
    # route can raise a meaningful error without knowing about HTTP.
    from core.rate_limit import RateLimitExceeded

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(
            status_code=429,
            content={"detail": exc.message},
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request, exc):
        return JSONResponse(status_code=401, content={"detail": exc.message})

    @app.exception_handler(AuthorizationError)
    async def authz_exception_handler(request, exc):
        return JSONResponse(status_code=403, content={"detail": exc.message})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request, exc):
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def validation_handler(request, exc):
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(ConfigurationError)
    async def configuration_handler(request, exc):
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @app.exception_handler(LLMProviderError)
    async def llm_provider_handler(request, exc):
        return JSONResponse(status_code=502, content={"detail": exc.message})

    @app.exception_handler(JobPilotException)
    async def jobpilot_exception_handler(request, exc):
        # Catch-all for domain errors without a more specific handler.
        logger.warning("domain_error", code=exc.code, message=exc.message)
        return JSONResponse(status_code=400, content={"detail": exc.message})

    # ── Include API routers ──────────────────────────────
    api_prefix = settings.API_V1_PREFIX

    from modules.ai.api.routes import router as ai_router
    from modules.analytics.api.routes import router as analytics_router
    from modules.applications.api.routes import router as applications_router
    from modules.auth.api.routes import router as auth_router
    from modules.calendar.api.routes import router as calendar_router
    from modules.config.api.routes import router as config_router
    from modules.cover_letters.api.routes import router as cover_letters_router
    from modules.jobs.api.routes import router as jobs_router
    from modules.notifications.api.routes import router as notifications_router
    from modules.resume.api.routes import router as resume_router
    from modules.search.api import router as search_router
    from modules.users.api.routes import router as users_router

    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(jobs_router, prefix=api_prefix)
    app.include_router(resume_router, prefix=api_prefix)
    app.include_router(cover_letters_router, prefix=api_prefix)
    app.include_router(applications_router, prefix=api_prefix)
    app.include_router(notifications_router, prefix=api_prefix)
    app.include_router(config_router, prefix=api_prefix)
    app.include_router(ai_router, prefix=api_prefix)
    app.include_router(calendar_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)
    app.include_router(search_router, prefix=api_prefix)

    # ── Public capability probe ──────────────────────────
    @app.get("/api/v1/meta", tags=["meta"])
    async def api_metadata():
        """What this instance supports, for the UI to adapt to.

        The client cannot otherwise tell whether the demo entry point exists,
        and rendering a button that always 503s is worse than hiding it.
        """
        return {
            "version": APP_VERSION,
            "demo_mode": settings.DEMO_MODE,
            "linkedin_oauth": bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET),
        }

    # ── Health checks ────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health_check():
        """Liveness: the process is up and serving. Never touches a dependency."""
        return {
            "status": "healthy",
            "version": APP_VERSION,
            "environment": settings.APP_ENV,
            "demo_mode": settings.DEMO_MODE,
        }

    @app.get("/health/ready", tags=["health"])
    async def readiness_check():
        """Readiness: the database and cache actually answer.

        An orchestrator routing traffic on liveness alone sends requests to a
        backend whose database is unreachable, so every one of them 500s.
        """
        checks = {"database": await _check_database(), "redis": await _check_redis()}
        ready = all(checks.values())
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ready" if ready else "degraded", "checks": checks},
        )

    return app


async def _check_database() -> bool:
    from sqlalchemy import text

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("healthcheck_database_failed", error=str(e))
        return False


async def _check_redis() -> bool:
    try:
        from core.redis_client import get_redis

        return bool(await (await get_redis()).ping())
    except Exception as e:
        logger.warning("healthcheck_redis_failed", error=str(e))
        return False


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )
