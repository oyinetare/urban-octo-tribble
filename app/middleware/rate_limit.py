import time

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core import redis_service


class TokenBucket:
    """
    Token algorithm bucket for rate limiting.

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
        if not redis_service.is_available:
            # If Redis is down, allow the request (fail open)
            return True, {"remaining": self.capacity}

        now = time.time()

        try:
            # Get current state
            state = await redis_service.get_rate_limit_state(user_id)

            if not state:
                # First request - initialize bucket
                await redis_service.set_rate_limit_state(
                    user_id, tokens=self.capacity - tokens, last_refill=now, ttl=60
                )
                return True, {"remaining": self.capacity - tokens}

            # Calculate refill
            last_refill = float(state["last_refill"])
            current_tokens = float(state["tokens"])
            time_passed = now - last_refill
            refill_amount = time_passed * self.refill_rate

            # Refill tokens (up to capacity)
            current_tokens = min(self.capacity, current_tokens + refill_amount)

            if current_tokens >= tokens:
                # Allow request
                new_tokens = current_tokens - tokens
                await redis_service.set_rate_limit_state(
                    user_id, tokens=new_tokens, last_refill=now, ttl=60
                )
                return True, {"remaining": int(new_tokens)}
            else:
                # Deny request
                return False, {"remaining": 0, "retry_after": 60}

        except Exception as e:
            print(f"Rate limiting error: {e}")
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

    # Get authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header:
        # Don't rate limit unauthenticated requests
        return await call_next(request)

    # Extract token
    try:
        token = auth_header.replace("Bearer ", "")
    except Exception:
        return await call_next(request)

    # Decode token to get user info
    try:
        from sqlmodel import select

        from app.core import token_manager
        from app.dependencies import get_session
        from app.models import User

        payload = token_manager.decode_token(token)
        if not payload:
            return await call_next(request)

        username = payload.get("sub")
        if not username:
            return await call_next(request)

        # Get user from database to check tier
        async for session in get_session():
            statement = select(User).where(User.username == username)
            result = await session.execute(statement)
            user = result.scalar_one_or_none()

            if not user or not user.id:
                return await call_next(request)

            # Determine rate limit based on user tier
            user_tier_limit = user.tier.limit

            bucket = TokenBucket(capacity=user_tier_limit, refill_rate=user_tier_limit / 60)

            # Check rate limit
            allowed, info = await bucket.consume(user.id)

            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={
                        "X-RateLimit-Limit": str(user_tier_limit),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": str(info["retry_after"]),
                    },
                )

            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            return response

    except Exception as e:
        print(f"Rate limiting error: {e}")
        # On error, allow the request
        return await call_next(request)
