import hashlib
import json
from collections.abc import Awaitable
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import redis_service


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle idempotency for POST requests.

    Clients send an Idempotency-Key header with POST requests.
    We cache the response in Redis and return it for duplicate requests.
    """

    def __init__(self, app, ttl_seconds: int = 86400):
        super().__init__(app)
        self.ttl_seconds = ttl_seconds

    async def dispatch(self, request: Request, call_next):
        # Only apply to POST requests
        if request.method != "POST":
            return await call_next(request)

        # Get idempotency key from header
        idempotency_key = request.headers.get("idempotency-key")

        # If no key provided, proceed normally
        if not idempotency_key:
            return await call_next(request)

        # Check if Redis is available
        if not redis_service.is_available or redis_service.client is None:
            return await call_next(request)

        # Read request body
        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()

        # Create Redis key
        redis_key = f"idempotency:{idempotency_key}"

        try:
            # Get Redis client (we know it's not None due to the check above)
            redis_client = redis_service.client

            # Check if we've seen this key before
            cached = await cast(Awaitable[dict], redis_client.hgetall(redis_key))

            if cached:
                # Verify body hash matches
                if cached.get("body_hash") != body_hash:
                    return Response(
                        content=json.dumps(
                            {
                                "success": False,
                                "error": "IdempotencyKeyReused",
                                "message": "Idempotency key was reused with different request body",
                            }
                        ),
                        status_code=422,
                        media_type="application/json",
                    )

                # Return cached response
                return Response(
                    content=cached.get("response_body"),
                    status_code=int(cached.get("status_code", 200)),
                    headers=json.loads(cached.get("headers", "{}")),
                    media_type=cached.get("media_type", "application/json"),
                )

            # Process the request
            response = await call_next(request)

            # Cache successful responses (2xx status codes)
            if 200 <= response.status_code < 300:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                # Extract headers
                headers_dict = dict(response.headers)

                # Store in Redis
                await cast(
                    Awaitable[int],
                    redis_client.hset(
                        redis_key,
                        mapping={
                            "body_hash": body_hash,
                            "response_body": response_body.decode(),
                            "status_code": str(response.status_code),
                            "headers": json.dumps(headers_dict),
                            "media_type": response.media_type or "application/json",
                        },
                    ),
                )
                await redis_client.expire(redis_key, self.ttl_seconds)

                # Return new response with body
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            return response

        except Exception as e:
            print(f"Idempotency middleware error: {e}")
            # On error, proceed with request
            return await call_next(request)
