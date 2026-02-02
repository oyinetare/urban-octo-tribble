import logging
import time

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core import services

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.

    Uses shared Redis service for state storage.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate

    async def consume(self, user_id: int, tokens: int = 1) -> tuple[bool, dict]:
        """
        Try to consume tokens from the bucket.

        Returns:
            (allowed, info_dict)
        """
        # Capture local reference and perform Type Guard
        redis = services.redis
        if redis is None or not redis.is_available:
            return True, {"remaining": self.capacity}

        now = time.time()
        try:
            # Since we verified 'redis' is not None, calling methods is safe
            state = await redis.get_rate_limit_state(user_id)

            if not state:
                # First request - initialize bucket
                await redis.set_rate_limit_state(
                    user_id, tokens=self.capacity - tokens, last_refill=now, ttl=60
                )
                return True, {"remaining": self.capacity - tokens}

            # Calculate refill
            last_refill = float(state["last_refill"])
            current_tokens = float(state["tokens"])
            time_passed = now - last_refill
            refill_amount = time_passed * self.refill_rate

            current_tokens = min(self.capacity, current_tokens + refill_amount)

            if current_tokens >= tokens:
                new_tokens = current_tokens - tokens
                await redis.set_rate_limit_state(
                    user_id, tokens=new_tokens, last_refill=now, ttl=60
                )
                return True, {"remaining": int(new_tokens)}

            # Deny request
            return False, {"remaining": 0, "retry_after": 60}

        except Exception as e:
            logger.exception(f"Rate limiting error: {e}")
            # On error, allow the request (fail open)
            return True, {"remaining": self.capacity}


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limit requests based on user authentication.

    Skips:
    - Health check endpoint
    - Unauthenticated requests

    Limits:
    - Free tier: 10 requests/minute
    - Paid tier: 100 requests/minute
    """
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    auth_header = request.headers.get("authorization")
    if not auth_header:
        return await call_next(request)

    try:
        token = auth_header.replace("Bearer ", "")
        from app.core import token_manager

        payload = token_manager.decode_token(token)
        if not payload:
            return await call_next(request)

        # 2. Extract and Validate (This fixes the __new__ error)
        raw_user_id = payload.get("id")
        raw_tier_limit = payload.get("tier_limit")

        # Use a type guard: ensure they are not None and are numbers
        if raw_user_id is None or raw_tier_limit is None:
            return await call_next(request)

        # Now it is safe to cast/use them
        user_id = int(raw_user_id)
        tier_limit = int(raw_tier_limit)

        bucket = TokenBucket(capacity=tier_limit, refill_rate=tier_limit / 60)
        allowed, info = await bucket.consume(user_id)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please upgrade your plan."},
                headers={
                    "X-RateLimit-Limit": str(tier_limit),
                    "Retry-After": str(info.get("retry_after", 60)),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        return response

    except Exception as e:
        # Fail open: don't block users if the limiter errors
        logger.error(f"Rate limiting failure: {e}")
        return await call_next(request)
