import hashlib
import json
from collections.abc import Awaitable
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Required to reconstruct the request stream
from starlette.types import Message

from app.core import services


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, ttl_seconds: int = 86400):
        super().__init__(app)
        self.ttl_seconds = ttl_seconds

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("idempotency-key")
        if not idempotency_key:
            return await call_next(request)

        redis_service = services.redis
        if redis_service is None or not redis_service.is_available:
            return await call_next(request)

        redis_client = redis_service.client
        if redis_client is None:
            return await call_next(request)

        body = await request.body()

        async def receive() -> Message:
            return {"type": "http.request", "body": body}

        # Override the request receive method so call_next can read the body again
        request._receive = receive
        # ----------------------------------------

        body_hash = hashlib.sha256(body).hexdigest()
        redis_key = f"idempotency:{idempotency_key}"

        try:
            cached = await cast(Awaitable[dict], redis_client.hgetall(redis_key))

            if cached:
                if cached.get("body_hash") != body_hash:
                    return Response(
                        content=json.dumps(
                            {
                                "success": False,
                                "error": "IdempotencyKeyReused",
                                "message": "Key reused with different body",
                            }
                        ),
                        status_code=422,
                        media_type="application/json",
                    )

                return Response(
                    content=cached.get("response_body"),
                    status_code=int(cached.get("status_code", 200)),
                    headers=json.loads(cached.get("headers", "{}")),
                    media_type=cached.get("media_type", "application/json"),
                )

            # Process original request (now safe because of the 'receive' override)
            response = await call_next(request)

            if 200 <= response.status_code < 300:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                await cast(
                    Awaitable[int],
                    redis_client.hset(
                        redis_key,
                        mapping={
                            "body_hash": body_hash,
                            "response_body": response_body.decode(),
                            "status_code": str(response.status_code),
                            "headers": json.dumps(dict(response.headers)),
                            "media_type": response.media_type or "application/json",
                        },
                    ),
                )
                await redis_client.expire(redis_key, self.ttl_seconds)

                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            return response

        except Exception as e:
            # Better to use your logger here
            print(f"Idempotency middleware error: {e}")
            return await call_next(request)
