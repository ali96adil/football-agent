import logging
import os
import hmac
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.routes.competitions import router as competitions_router
from app.api.routes.fixtures import router as fixtures_router
from app.api.routes.standings import router as standings_router
from app.api.routes.sync import router as sync_router
from app.db.connection import lifespan, pool
from app.api.routes.snapshots import router as snapshots_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.auth import router as auth_router, users_router
from app.auth import CSRF_COOKIE, audit, current_user
from app.security import hash_secret
from app.api.routes.fixtures_browser import router as fixtures_browser_router
from app.api.routes.predictions import (
    router as predictions_router,
)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("football-collector")


app = FastAPI(
    title="Football Intelligence Collector",
    description="Data collection service for the Football Intelligence Platform.",
    version=os.getenv("APP_VERSION", "1.0.0-dev.2"),
    lifespan=lifespan,
)


app.include_router(competitions_router)
app.include_router(fixtures_router)
app.include_router(standings_router)
app.include_router(sync_router)

app.include_router(snapshots_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(predictions_router)
app.include_router(fixtures_browser_router)


@app.middleware("http")
async def enforce_product_access(request: Request, call_next):
    path = request.url.path
    public = path in {"/", "/health", "/api/v1/auth/login"} or path.startswith("/docs") or path.startswith("/openapi")
    protected = path.startswith("/api/") or path == "/sources"
    if public or not protected or path.startswith("/api/v1/auth/"):
        return await call_next(request)
    try:
        user = await current_user(request)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not user.has("operate"):
                async with pool.connection() as connection:
                    await audit(connection, action="http.write", outcome="denied", request=request, actor=user, details={"path": path})
                return JSONResponse(status_code=403, content={"detail": "operator permission required"})
            csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
            csrf_header = request.headers.get("x-csrf-token", "")
            if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header) or not hmac.compare_digest(hash_secret(csrf_header), request.state.csrf_hash):
                return JSONResponse(status_code=403, content={"detail": "invalid CSRF token"})
        request.state.current_user = user
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "football-collector",
        "status": "running",
        "version": os.getenv("APP_VERSION", "1.0.0-dev.2"),
        "revision": os.getenv("GIT_REVISION", "unknown"),
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        async with pool.connection() as connection:
            result = await connection.execute(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    NOW() AS database_time
                """
            )

            database_info = await result.fetchone()

        return {
            "status": "healthy",
            "service": "football-collector",
            "database": database_info,
        }

    except Exception as exc:
        logger.exception("Database health check failed")

        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from exc


@app.get("/sources")
async def list_sources() -> dict[str, Any]:
    try:
        async with pool.connection() as connection:
            result = await connection.execute(
                """
                SELECT
                    id,
                    code,
                    name,
                    source_type,
                    enabled,
                    priority,
                    reliability_score,
                    daily_request_limit,
                    reserved_requests,
                    requests_used_today,
                    last_success_at,
                    last_failure_at,
                    metadata,
                    created_at,
                    updated_at
                FROM core.data_sources
                ORDER BY priority DESC, id
                """
            )

            sources = await result.fetchall()

        return {
            "count": len(sources),
            "sources": sources,
        }

    except Exception as exc:
        logger.exception("Unable to retrieve data sources")

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve data sources",
        ) from exc
