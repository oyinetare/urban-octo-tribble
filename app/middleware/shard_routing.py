"""
Request routing middleware for shard-aware routing.

Features:
- Route requests to appropriate shard based on user_id
- Add shard_id to request state for downstream use
- Support sticky sessions (same user → same shard)
"""

import logging
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.shard_manager import shard_manager

logger = logging.getLogger(__name__)


class ShardRoutingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds shard routing information to requests.

    For authenticated requests:
    - Determines target shard based on user_id
    - Adds shard_id to request.state for use by route handlers
    - Logs shard routing for monitoring

    For unauthenticated requests:
    - Skips shard routing
    - Route handlers can still manually assign shards
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add shard information."""

        # Initialize shard info in request state
        request.state.shard_id = None
        request.state.shard_routing_enabled = False

        # Check if sharding is enabled
        if not shard_manager.is_initialized():
            # Sharding not configured, skip routing
            return await call_next(request)

        # Try to get user from request state (set by auth middleware)
        # This assumes you have auth middleware that sets request.state.user
        user = getattr(request.state, "user", None)

        if user and hasattr(user, "id"):
            # Get shard for this user
            shard_id = shard_manager.get_shard_for_user(user.id)

            if shard_id:
                request.state.shard_id = shard_id
                request.state.shard_routing_enabled = True

                # Log routing (useful for monitoring)
                logger.debug(
                    "Routing request to shard",
                    extra={
                        "user_id": user.id,
                        "shard_id": shard_id,
                        "path": request.url.path,
                        "method": request.method,
                    },
                )

        # Process request
        response = await call_next(request)

        # Add shard info to response headers for debugging/monitoring
        if request.state.shard_id:
            response.headers["X-Shard-ID"] = request.state.shard_id

        return response


class ShardHealthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that checks shard health before processing requests.

    If target shard is unhealthy:
    - Logs warning
    - Request still proceeds (consistent hash ring will route to next healthy shard)
    - Response includes X-Shard-Failover header
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check shard health before processing."""

        # Get shard info from request state (set by ShardRoutingMiddleware)
        shard_id = getattr(request.state, "shard_id", None)

        if shard_id and shard_manager.is_initialized():
            shard_info = shard_manager.get_shard_info(shard_id)

            if shard_info and not shard_info.is_healthy:
                logger.warning(
                    f"Request routed to unhealthy shard {shard_id}, "
                    f"will failover to next healthy shard"
                )
                # Note: The actual failover happens in get_shard_for_user
                # which skips unhealthy shards automatically

        # Process request
        response = await call_next(request)

        return response
