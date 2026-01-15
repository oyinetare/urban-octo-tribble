from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core import get_settings, redis_service
from app.exceptions import AppException
from app.middleware import https_redirect_middleware, security_headers_middleware
from app.routes import auth, documents, users

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
    await init_db()
    await redis_service.initialize()

    yield

    # Shutdown
    await redis_service.close()


app = FastAPI(
    title="urban-octo-tribble API",
    version="1.0.0",
    lifespan=lifespan,
    # Add OAuth2 scopes documentation (only in development)
    swagger_ui_init_oauth={
        "clientId": "swagger",
        "appName": "Jubilant-Barnacle API",
        "scopes": "read write admin moderate",
    }
    if settings.ENVIRONMENT == "development"
    else None,
    # middleware=[Middleware(CustomMiddleware)]
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Trusted Host
app.add_middleware(
    TrustedHostMiddleware,  # type: ignore[arg-type]
    allowed_hosts=["localhost", "127.0.0.1"],
)

# 4. Security Headers
app.middleware("http")(security_headers_middleware)

# 5. Rate Limiting
# app.middleware("http")(rate_limit_middleware)


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


# ROUTES
api_prefix = "/api/v1"
app.include_router(users.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)


@app.get("/")
def root():
    return {
        "message": "Welcome to urban-octo-tribble API",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status and service availability
    """
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "services": {
            "redis": redis_service.is_available,
        },
    }
