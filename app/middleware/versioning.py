from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add deprecation warnings for old API versions.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add deprecation headers for v1
        if request.url.path.startswith("/api/v1"):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "Sat, 31 Dec 2025 23:59:59 GMT"
            response.headers["Link"] = '</api/v2>; rel="successor-version"'

        return response
