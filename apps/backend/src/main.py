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

from core.config import settings
from core.database import get_engine, dispose_db
from core.redis_client import close_redis
from core.logger import get_logger
from core.middleware import RequestLoggingMiddleware, AuthMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────
    logger.info("Starting JobPilot AI...", extra={"env": settings.APP_ENV})
    engine = get_engine()
    if engine:
        logger.info("Database connection established")
        # Auto-create tables in development mode
        if settings.APP_ENV == "development":
            from core.database import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created/verified")
    yield
    # ── Shutdown ─────────────────────────────────────────
    logger.info("Shutting down JobPilot AI...")
    await dispose_db()
    await close_redis()
    logger.info("Database and Redis connections closed")


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
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuthMiddleware)

    # Exception handlers
    from starlette.responses import JSONResponse
    from core.exceptions import (
        JobPilotException, NotFoundError, ValidationError,
        AuthenticationError, AuthorizationError,
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

    # ── Include API routers ──────────────────────────────
    api_prefix = settings.API_V1_PREFIX

    from modules.auth.api.routes import router as auth_router
    from modules.users.api.routes import router as users_router
    from modules.jobs.api.routes import router as jobs_router
    from modules.resume.api.routes import router as resume_router
    from modules.cover_letters.api.routes import router as cover_letters_router
    from modules.applications.api.routes import router as applications_router
    from modules.notifications.api.routes import router as notifications_router
    from modules.config.api.routes import router as config_router
    from modules.ai.api.routes import router as ai_router
    from modules.calendar.api.routes import router as calendar_router
    from modules.analytics.api.routes import router as analytics_router
    from modules.search.api import router as search_router

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

    # ── Health check ─────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.APP_ENV,
        }

    return app


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
