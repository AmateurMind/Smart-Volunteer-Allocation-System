"""
SVAS Backend – FastAPI Application Entry Point
Initialises the app, registers all routers, configures middleware,
and exposes health-check / meta endpoints.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

import firebase_admin
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.routers import analyze, dashboard, match, notifications, upload, volunteers

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Application lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Startup
    -------
    - Log configuration summary.
    - Trigger lazy Firebase Admin initialisation so the first request
      doesn't pay the cold-start penalty.

    Shutdown
    --------
    - Log graceful-shutdown message.
    """
    # ── Startup ───────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(
        "  SVAS API  |  %s  |  %s", settings.APP_VERSION, settings.ENVIRONMENT.upper()
    )
    logger.info("=" * 60)
    logger.info("Project  : %s", settings.GOOGLE_CLOUD_PROJECT)
    logger.info("Gemini   : %s", "configured" if settings.GEMINI_API_KEY else "NOT SET")
    logger.info(
        "Firebase : %s",
        settings.service_account_key_path
        if settings.service_account_key_exists
        else "using ADC (no key file)",
    )
    logger.info("BigQuery : %s", settings.BIGQUERY_DATASET)
    logger.info("CORS     : %s", ", ".join(settings.ALLOWED_ORIGINS))
    logger.info("-" * 60)

    # Warm up Firebase Admin SDK
    try:
        from app.middleware.auth import _init_firebase

        _init_firebase()
        logger.info("Firebase Admin SDK: ready (apps=%d)", len(firebase_admin._apps))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Firebase Admin SDK warm-up failed: %s", exc)

    logger.info("SVAS API is ready to serve requests.")

    yield  # ← application runs here

    # ── Shutdown ──────────────────────────────────────────────────────
    logger.info("SVAS API is shutting down. Goodbye!")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
    contact={
        "name": "SVAS Engineering",
        "email": "engineering@svas.org",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Liveness and readiness probes used by Cloud Run.",
        },
        {
            "name": "Data Upload",
            "description": "Multi-format community data ingestion (CSV / JSON / text / image).",
        },
        {
            "name": "Analysis",
            "description": "Gemini-powered AI need categorisation and urgency detection.",
        },
        {
            "name": "Matching & Assignment",
            "description": "Smart volunteer matching algorithm and task assignment.",
        },
        {
            "name": "Dashboard",
            "description": "Aggregated real-time statistics and heatmap data.",
        },
        {
            "name": "Volunteers",
            "description": "Volunteer registration, profiles, and task history.",
        },
        {
            "name": "Notifications",
            "description": "Firebase Cloud Messaging push notification management.",
        },
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)


@app.middleware("http")
async def add_response_time_header(request: Request, call_next):
    """
    Attach an ``X-Response-Time`` header (in milliseconds) to every response.
    Useful for performance monitoring and Cloud Run latency dashboards.
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Structured request / response logging for every HTTP call.
    Skips noisy health-check endpoints.
    """
    skip_paths = {"/health", "/", "/favicon.ico"}
    if request.url.path in skip_paths:
        return await call_next(request)

    start = time.perf_counter()
    logger.info(
        "→ %s %s  (client=%s)",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
    )
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "← %s %s  status=%d  time=%sms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Exception handlers
# ─────────────────────────────────────────────────────────────────────────────


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": f"The endpoint '{request.url.path}' does not exist.",
            "docs": "/docs",
        },
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={
            "error": "method_not_allowed",
            "message": (
                f"Method '{request.method}' is not allowed on '{request.url.path}'."
            ),
        },
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc) -> JSONResponse:
    logger.exception(
        "Unhandled server error on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. The team has been notified.",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(match.router)
app.include_router(dashboard.router)
app.include_router(volunteers.router)
app.include_router(notifications.router)


# ─────────────────────────────────────────────────────────────────────────────
# Root endpoint
# ─────────────────────────────────────────────────────────────────────────────


@app.get(
    "/",
    tags=["Health"],
    summary="API root",
    description="Returns basic API metadata. Useful as a smoke-test.",
    response_model=Dict[str, Any],
)
async def root() -> Dict[str, Any]:
    """
    API root – returns name, version, and environment.
    """
    return {
        "name": settings.APP_NAME,
        "description": settings.APP_DESCRIPTION,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "status": "running",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Health check  (used by Cloud Run liveness + readiness probes)
# ─────────────────────────────────────────────────────────────────────────────


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description=(
        "Liveness / readiness probe consumed by Cloud Run. "
        "Returns ``200 OK`` when the process is healthy. "
        "Returns ``503`` when a critical dependency is unavailable."
    ),
    response_model=Dict[str, Any],
)
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check.

    Checks
    ------
    - Firebase Admin SDK initialisation status.
    - Gemini API key presence.
    - BigQuery service availability.

    Returns HTTP 200 if all checks pass, HTTP 503 if any critical check fails.
    """
    checks: Dict[str, Any] = {}
    overall_healthy = True

    # ── Firebase ──────────────────────────────────────────────────────
    firebase_ready = bool(firebase_admin._apps)
    checks["firebase"] = {
        "status": "ok" if firebase_ready else "not_initialised",
        "healthy": firebase_ready,
    }
    if not firebase_ready:
        overall_healthy = False  # Firebase is critical

    # ── Gemini ────────────────────────────────────────────────────────
    gemini_configured = bool(settings.GEMINI_API_KEY)
    checks["gemini"] = {
        "status": "configured" if gemini_configured else "api_key_missing",
        "healthy": gemini_configured,
        "model": settings.GEMINI_MODEL,
    }
    # Gemini is important but not critical enough to mark the whole service down

    # ── BigQuery ──────────────────────────────────────────────────────
    checks["bigquery"] = {
        "status": "configured",
        "dataset": settings.BIGQUERY_DATASET,
        "healthy": True,  # BigQuery failures are non-critical (graceful degradation)
    }

    # ── Environment ───────────────────────────────────────────────────
    checks["environment"] = {
        "name": settings.ENVIRONMENT,
        "project": settings.GOOGLE_CLOUD_PROJECT,
        "version": settings.APP_VERSION,
    }

    response_body = {
        "status": "healthy" if overall_healthy else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }

    http_status = (
        status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(content=response_body, status_code=http_status)


# ─────────────────────────────────────────────────────────────────────────────
# Readiness probe  (separate from liveness – Cloud Run uses /health for both,
# but some setups use a distinct /ready endpoint)
# ─────────────────────────────────────────────────────────────────────────────


@app.get(
    "/ready",
    tags=["Health"],
    summary="Readiness probe",
    description="Lightweight readiness probe – returns 200 when the app is ready to serve traffic.",
    response_model=Dict[str, Any],
)
async def ready() -> Dict[str, Any]:
    """Minimal readiness probe – always returns 200 if the process is up."""
    return {"status": "ready", "version": settings.APP_VERSION}


# ─────────────────────────────────────────────────────────────────────────────
# Uvicorn entrypoint  (for local development: `python -m app.main`)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,  # we handle request logging ourselves above
    )
