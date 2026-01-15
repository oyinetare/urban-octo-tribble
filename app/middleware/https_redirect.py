"""HTTPS enforcement middleware."""

from fastapi import Request, status
from fastapi.responses import RedirectResponse

from app.core import get_settings

settings = get_settings()


async def https_redirect_middleware(request: Request, call_next):
    """
    Redirect HTTP requests to HTTPS in production.

    This middleware:
    1. Checks if running in production
    2. Checks if request is HTTP (not HTTPS)
    3. Redirects to HTTPS version of the URL

    Skips:
    - Non-production environments
    - Health check endpoint
    - Requests already on HTTPS
    - Requests from localhost (development)
    """
    # Skip in development or if already HTTPS
    if settings.ENVIRONMENT != "production" or request.url.scheme == "https":
        return await call_next(request)

    # Skip for localhost (development)
    if request.url.hostname in ["localhost", "127.0.0.1"]:
        return await call_next(request)

    # Skip for health check (some load balancers use HTTP for health checks)
    if request.url.path == "/health":
        return await call_next(request)

    # Redirect HTTP to HTTPS
    https_url = request.url.replace(scheme="https")
    return RedirectResponse(
        url=str(https_url),
        status_code=status.HTTP_308_PERMANENT_REDIRECT,  # Permanent redirect, maintains method
    )
