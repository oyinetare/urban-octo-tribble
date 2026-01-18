# app/main.py
from collections.abc import Awaitable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core import redis_service  # ✅ Don't import notification_service from core
from app.core.taskiq_broker import broker
from app.exceptions import AppException
from app.middleware import (
    https_redirect_middleware,
    rate_limit_middleware,
    security_headers_middleware,
)
from app.routes import auth, documents, notifications, users

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db
    from app.core.notification import NotificationService

    """
    Lifespan context manager for startup and shutdown events.
    """
    # ========================================================================
    # STARTUP
    # ========================================================================

    print("🚀 Starting urban-octo-tribble API...")

    # Initialize database
    await init_db()

    # Initialize Redis
    await redis_service.initialize()

    # Initialize TaskIQ broker (for task submission, not worker)
    if not broker.is_worker_process:
        await broker.startup()
        print("✅ TaskIQ broker initialized (submit mode)")

    # Create notification service (not used in main, just for initialization)
    # The actual service is accessed via dependency injection
    _ = NotificationService()  # ✅ Create but don't assign to variable
    print("✅ NotificationService initialized")

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    print("🛑 Shutting down Jubilant-Barnacle API...")

    # Shutdown TaskIQ broker
    if not broker.is_worker_process:
        await broker.shutdown()
        print("✅ TaskIQ broker shutdown")

    # Close Redis connection
    await redis_service.close()

    print("👋 Shutdown complete")


app = FastAPI(
    title="urban-octo-tribble API",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "clientId": "swagger",
        "appName": "Jubilant-Barnacle API",
        "scopes": "read write admin moderate",
    }
    if settings.ENVIRONMENT == "development"
    else None,
)


# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

app.middleware("http")(https_redirect_middleware)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,  # type: ignore[arg-type]
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"],
)

app.middleware("http")(security_headers_middleware)
app.middleware("http")(rate_limit_middleware)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
        headers=exc.headers or {},
    )


# =============================================================================
# ROUTES
# =============================================================================
api_prefix = "/api/v1"
app.include_router(users.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(documents.redirect_router)
app.include_router(notifications.router, prefix=api_prefix)  # ✅ Add prefix


@app.get("/")
def root():
    """Root endpoint."""
    response = {
        "message": "Welcome to Jubilant-Barnacle API",
        "version": "1.0.0",
    }

    if settings.ENVIRONMENT == "development":
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"
        response["oauth2_scopes"] = {
            "read": "Read access to resources",
            "write": "Write access to resources",
            "admin": "Admin access to all resources",
            "moderate": "Moderate content",
        }

    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    queue_sizes = {}
    if redis_service.is_available and redis_service.client:
        try:
            main_queue = await cast(Awaitable[int], redis_service.client.llen("taskiq:main"))
            dlq_queue = await cast(Awaitable[int], redis_service.client.llen("queue:webhooks:dlq"))
            queue_sizes = {
                "main_queue": main_queue,
                "dead_letter_queue": dlq_queue,
            }
        except Exception:
            queue_sizes = {"error": "Failed to fetch queue sizes"}

    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "services": {
            "redis": redis_service.is_available,
            "taskiq": broker.is_worker_process or redis_service.is_available,
        },
        "queues": queue_sizes if redis_service.is_available else None,
    }
