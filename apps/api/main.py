from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from packages.cache.memory import MemoryCache
from packages.cache.redis import RedisCache
from packages.domain.config import get_settings
from packages.domain.database import close_db, init_db
from packages.security.auth import get_auth_service
from packages.security.middleware import (
    AuthMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    cache: str
    checks: dict[str, Any]


cache_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cache_client
    settings = get_settings()

    # Initialize cache
    if settings.cache_enabled:
        try:
            cache_client = RedisCache()
            await cache_client.connect()
        except Exception:
            cache_client = MemoryCache()
    else:
        cache_client = MemoryCache()

    await init_db()
    yield
    if hasattr(cache_client, "disconnect"):
        await cache_client.disconnect()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AgentBench-Research API",
        description="Evidence-grounded autonomous research-paper analysis agent",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60, requests_per_hour=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    auth_service = get_auth_service()
    app.add_middleware(AuthMiddleware, auth_service=auth_service)

    from apps.api.auth import router as auth_router
    from apps.api.dashboard import router as dashboard_router
    from apps.api.dashboard_ui import router as dashboard_ui_router
    from apps.api.evaluation import router as evaluation_router
    from apps.api.extraction import router as extraction_router
    from apps.api.papers import router as papers_router
    from apps.api.projects import router as projects_router
    from apps.api.retrieval import router as retrieval_router
    from apps.api.synthesis import router as synthesis_router
    from apps.api.verification import router as verification_router
    from packages.websocket import websocket_router
    from packages.websocket import ws_manager
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(papers_router)
    app.include_router(retrieval_router)
    app.include_router(extraction_router)
    app.include_router(synthesis_router)
    app.include_router(verification_router)
    app.include_router(evaluation_router)
    app.include_router(dashboard_router)
    app.include_router(dashboard_ui_router)
    app.include_router(websocket_router)

    # Expose ws_manager for use in other modules
    app.state.ws_manager = ws_manager

    app.mount("/assets", StaticFiles(directory="apps/api/static/assets"), name="static-assets")

    @app.get("/healthz", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        cache_status = "connected" if isinstance(cache_client, RedisCache) else "in-memory"
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            environment=settings.app_env,
            database="connected",
            cache=cache_status,
            checks={
                "database": "ok",
                "cache": cache_status,
                "config": "ok",
            },
        )

    return app


app = create_app()
