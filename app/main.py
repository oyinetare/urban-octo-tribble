import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core import get_settings, services
from app.exceptions import AppException
from app.middleware import (
    IdempotencyMiddleware,
    ShardRoutingMiddleware,
    https_redirect_middleware,
    log_requests_middleware,
    rate_limit_middleware,
    security_headers_middleware,
)
from app.routes import auth, documents, metrics, query, users

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    https://uvicorn.dev/concepts/lifespan/

    Lifespan context manager for startup and shutdown events.

    Since Uvicorn is an ASGI server, it supports the ASGI lifespan protocol. This allows you to run startup and shutdown events for your application.

    The lifespan protocol is useful for initializing resources that need to be available throughout the lifetime of the application, such as database connections, caches, or other services.

    Keep in mind that the lifespan is executed only once per application instance. If you have multiple workers, each worker will execute the lifespan independently.

    Startup:
    - Initialize all services (storage, AI, events, etc.)
    - Initialize database

    Shutdown:
    - Close event producer gracefully
    - Close Redis connections
    - Clean up resources
    """
    # ========== STARTUP ==========
    logger.info("🚀 Starting application...")

    # Initialize all services (including events)
    await services.init()

    # Initialize database
    from app.core import init_db

    await init_db()

    logger.info("✅ Application started successfully")

    yield

    # ========== SHUTDOWN ==========
    logger.info("🛑 Shutting down application...")

    # Gracefully shutdown services
    await services.shutdown()

    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title="urban-octo-tribble API",
    version="1.0.0",
    lifespan=lifespan,
    # redirect_slashes=False,
    # Add OAuth2 scopes documentation (only in development)
    swagger_ui_init_oauth={
        "clientId": "swagger",
        "appName": "Jubilant-Barnacle API",
        "scopes": "read write admin moderate",
    }
    if settings.ENVIRONMENT == "development"
    else None,
)


# MIDDLEWARE CONFIGURATION
# Order matters! Middleware is executed in reverse order of addition.

# 1. HTTPS Redirect - Should be first (executed last)
app.middleware("http")(https_redirect_middleware)

# 2. CORS - Must be early
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=[
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:8089",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Trusted Host
app.add_middleware(
    TrustedHostMiddleware,  # type: ignore[arg-type]
    allowed_hosts=["localhost", "127.0.0.1", "testserver"],
)

# 4. Security Headers
app.middleware("http")(security_headers_middleware)

# 5. Idempotency (for POST requests)
app.add_middleware(IdempotencyMiddleware, ttl_seconds=86400)  # type: ignore[arg-type]

# 6. Logging
app.middleware("http")(log_requests_middleware)

# 7. Rate Limiting
app.middleware("http")(rate_limit_middleware)

# 8. Shard Routing
# This should be last in the code (executed first in the request cycle)
# so the correct database/tenant is identified before any logic runs.
app.add_middleware(ShardRoutingMiddleware)  # type: ignore[arg-type]


# 9. Simple Auth Middleware (NEW)
# Added LAST so it executes FIRST in the request cycle.
# It sets request.state.user so ShardRoutingMiddleware can see it.
@app.middleware("http")
async def quick_auth_middleware(request: Request, call_next):
    # logic to get user from token/session
    # request.state.user = await get_user_from_token(request.headers.get("Authorization"))
    return await call_next(request)


# EXCEPTION HANDLERS
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


# ROUTES Debug
# Debug endpoint to see all registered routes
# @app.get("/debug/routes")
# def list_routes():
#     """Debug endpoint to see all registered routes."""
#     routes = []
#     for route in app.routes:
#         if hasattr(route, "methods"):
#             routes.append({
#                 "path": route.path,
#                 "name": route.name,
#                 "methods": list(route.methods)
#             })
#     return {"routes": routes}

# --- GLOBAL ENDPOINTS (No Versioning/Minimal Middleware impact) ---


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Welcome to urban-octo-tribble API",
        "version": "1.0.0",
        "features": ["RAG", "Vector Search", "Event Streaming, Rate Limiting"],
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Comprehensive readiness probe for all infrastructure dependencies."""

    async def check_redis():
        return await services.redis.ping() if services.redis else False

    async def check_storage():
        if not services.storage:
            return False
        try:
            await services.storage.file_exists("__health_check__")
            return True
        except Exception:
            return False

    async def check_qdrant():
        if not services.vector_store:
            return False
        try:
            collections = await services.vector_store.async_client.get_collections()
            return collections is not None
        except Exception:
            return False

    async def check_database():
        try:
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False

    async def check_llm():
        """Check if LLM provider is responding"""
        # Simplified return to satisfy the 'negated condition' hint
        return bool(services.rag and services.rag.llm_service)

    async def check_embeddings():
        """Check if the local model is loaded in RAM"""
        return not (not services.embedding or services.embedding.model is None)

    async def check_metrics():
        """Check if the performance metrics is ready"""
        return not (not services.metrics or services.metrics.is_available is False)

    async def check_events():
        """Check if event producer is initialized and ready."""
        return bool(services.events and services.events.is_initialized)

    # Run all checks in parallel
    results = await asyncio.gather(
        check_redis(),
        check_storage(),
        check_qdrant(),
        check_llm(),
        check_embeddings(),
        check_database(),
        check_metrics(),
        check_events(),
        return_exceptions=True,
    )

    # Safely unpack results
    (
        redis_ok,
        storage_ok,
        qdrant_ok,
        llm_ok,
        embed_ok,
        db_ok,
        metrics_ok,
        events_ok,
    ) = [res if isinstance(res, bool) else False for res in results]

    health_status = {
        "redis": redis_ok,
        "storage": storage_ok,
        "vector_store": qdrant_ok,
        "llm_provider": llm_ok,
        "embedding_model": embed_ok,
        "metrics": metrics_ok,
        "database": db_ok,
        "events": events_ok,
    }

    is_ready = all(health_status.values())

    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if is_ready else "unready", "dependencies": health_status},
    )


# --- ROUTERS ---

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(query.router, prefix="/api/v1/query", tags=["Query"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
# Redirect router WITHOUT api prefix (for cleaner URLs like /d/abc123)
app.include_router(documents.redirect_router)
