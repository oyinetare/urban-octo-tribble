import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core import get_settings, services
from app.exceptions import AppException
from app.middleware import (
    IdempotencyMiddleware,
    # VersioningMiddleware,
    https_redirect_middleware,
    log_requests_middleware,
    rate_limit_middleware,
    security_headers_middleware,
)
from app.routes import auth, documents, search, users

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db

    """
    https://uvicorn.dev/concepts/lifespan/

    Lifespan context manager for startup and shutdown events.

    Since Uvicorn is an ASGI server, it supports the ASGI lifespan protocol. This allows you to run startup and shutdown events for your application.

    The lifespan protocol is useful for initializing resources that need to be available throughout the lifetime of the application, such as database connections, caches, or other services.

    Keep in mind that the lifespan is executed only once per application instance. If you have multiple workers, each worker will execute the lifespan independently.

    Startup:
    - Initialize connections

    Shutdown:
    - Close connections
    """
    # Startup
    # Initialize storage

    await services.init()

    await init_db()

    yield

    # Shutdown
    if services.redis:
        await services.redis.close()


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
    allowed_hosts=["localhost", "127.0.0.1", "testserver"],  # Ensure testserver is here
)

# 4. Security Headers
app.middleware("http")(security_headers_middleware)

# 5. Versioning Headers
# app.add_middleware(VersioningMiddleware)

# 6. Idempotency (for POST requests)
app.add_middleware(IdempotencyMiddleware, ttl_seconds=86400)  # type: ignore[arg-type]

# 7. Logging
app.middleware("http")(log_requests_middleware)

# 8. Rate Limiting
app.middleware("http")(rate_limit_middleware)


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
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Comprehensive Readiness probe for all infrastructure dependencies.
    Returns 200 if all are ready, 503 if any are down.
    """

    async def check_redis():
        if services.redis is None:
            return False
        return await services.redis.ping()

    async def check_storage():
        """Check if storage is accessible"""
        if not services.storage:
            return False
        try:
            # Simple check - storage responds to API calls
            await services.storage.file_exists("__health_check__")
            return True
        except Exception:
            return False

    async def check_qdrant():
        if services.vector_store is None:
            return False
        try:
            # Check connection and verify collections can be retrieved
            collections = await services.vector_store.async_client.get_collections()
            return collections is not None
        except Exception:
            return False

    # Run all checks in parallel for performance
    redis_ok, storage_ok, qdrant_ok = await asyncio.gather(
        check_redis(), check_storage(), check_qdrant(), return_exceptions=True
    )

    health_status = {
        "redis": redis_ok is True,
        "storage": storage_ok is True,
        "vector_store": qdrant_ok is True,
        "database": True,  # TODO: Add actual DB ping
    }

    is_ready = all(health_status.values())

    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if is_ready else "unready", "dependencies": health_status},
    )


# --- ROUTERS ---


app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
# Redirect router WITHOUT api prefix (for cleaner URLs like /d/abc123)
app.include_router(documents.redirect_router)
