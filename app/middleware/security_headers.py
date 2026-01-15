"""
Security headers middleware with configurable CSP.

Provides two CSP modes:
1. Development mode: Permissive CSP for Swagger UI
2. Production mode: Strict CSP (disable Swagger UI in production)
"""

from fastapi import Request

from app.core import get_settings

settings = get_settings()


async def security_headers_middleware(request: Request, call_next):
    """
    Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS protection)
    - Strict-Transport-Security: HSTS for HTTPS
    - Content-Security-Policy: CSP
    - Referrer-Policy: Referrer policy
    - Permissions-Policy: Permissions policy
    """
    response = await call_next(request)

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # XSS Protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # HSTS (only in production with HTTPS)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Content Security Policy
    # Different CSP for docs vs API endpoints
    is_docs_endpoint = (
        request.url.path.startswith("/docs")
        or request.url.path.startswith("/redoc")
        or request.url.path.startswith("/openapi.json")
    )

    if is_docs_endpoint and settings.ENVIRONMENT == "development":
        # Permissive CSP for Swagger UI in development
        csp_directives = [
            "default-src 'self'",
            # Allow inline scripts and styles for Swagger UI
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net",
            # Allow connections to CDN for source maps and resources
            "connect-src 'self' https://cdn.jsdelivr.net",
            "font-src 'self' data: https://cdn.jsdelivr.net",
        ]
    else:
        # Strict CSP for API endpoints (production-ready)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "connect-src 'self'",
            "font-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests",
        ]

    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

    return response
