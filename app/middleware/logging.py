import logging
import time

from fastapi import Request

logger = logging.getLogger(__name__)


async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()

    # Safely get the client host
    client_host = request.client.host if request.client else "unknown"

    # Log request
    logger.info(
        "request_started",
        extra={"method": request.method, "path": request.url.path, "client": client_host},
    )

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "duration_ms": duration_ms,
            },
        )
        raise  # Distinguish from errors in exception handling [as per your previous instruction]
