"""Background tasks for webhook delivery."""

import logging
from typing import Any

import httpx
from sqlmodel import select
from taskiq import Context

from app.core.taskiq_broker import broker
from app.models import User

logger = logging.getLogger(__name__)

try:
    from taskiq.exceptions import TaskiqRetry
except ImportError:
    # Fallback for environments where taskiq is missing or outdated
    class TaskiqRetry(Exception):
        def __init__(self, delay: int = 0, labels: dict | None = None):
            self.delay = delay
            self.labels = labels or {}
            super().__init__()


def generate_webhook_signature(payload: dict, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    import hashlib
    import hmac
    import json

    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_json.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return signature


@broker.task(
    retry_on_error=True,
    max_retries=3,
    task_name="send_webhook",
)
async def send_webhook_task(
    notification_id: int,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    action_url: str | None,
    timestamp: str,
    context: Context | None = None,
) -> dict[str, Any]:
    """Send webhook notification to user's configured endpoint."""
    retry_count = 0
    if context and hasattr(context, "message") and context.message:
        retry_count = context.message.labels.get("retry_count", 0)

    logger.info(
        f"Processing webhook for notification {notification_id} (attempt {retry_count + 1}/4)"
    )

    if not context or not hasattr(context.state, "session_factory"):
        logger.error("No database session factory in worker state")
        return {"success": False, "error": "Worker not properly initialized"}

    session_factory = context.state.session_factory

    async with session_factory() as session:
        statement = select(User).where(User.id == user_id)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User {user_id} not found")
            return {"success": False, "error": "User not found"}

        if not user.webhook_url:
            logger.info(f"User {user_id} has no webhook URL configured")
            return {"success": True, "skipped": "No webhook URL"}

        webhook_url = user.webhook_url
        webhook_secret = "your-secret-key"

    payload = {
        "type": notification_type,
        "title": title,
        "message": message,
        "action_url": action_url,
        "timestamp": timestamp,
        "notification_id": notification_id,
    }

    signature = generate_webhook_signature(payload, webhook_secret)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-ID": str(notification_id),
        "X-Webhook-Timestamp": timestamp,
        "User-Agent": "Jubilant-Barnacle-Webhook/1.0",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
                follow_redirects=False,
            )

            if response.status_code in (200, 201, 202, 204):
                logger.info(
                    f"Webhook delivered successfully for notification {notification_id} "
                    f"(status: {response.status_code})"
                )
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "attempt": retry_count + 1,
                }

            logger.warning(
                f"Webhook failed with status {response.status_code} "
                f"for notification {notification_id}"
            )
            raise TaskiqRetry(
                delay=_calculate_retry_delay(retry_count),
                labels={"retry_count": retry_count + 1},
            ) from None

    except httpx.TimeoutException as e:
        logger.error(
            f"Webhook timeout for notification {notification_id}: {e} "
            f"(attempt {retry_count + 1}/4)"
        )
        if retry_count >= 3:
            await _send_to_dead_letter_queue(
                notification_id, user_id, payload, "Timeout after 4 attempts"
            )
            return {"success": False, "error": "Timeout - sent to DLQ"}

        raise TaskiqRetry(
            delay=_calculate_retry_delay(retry_count),
            labels={"retry_count": retry_count + 1},
        ) from e

    except httpx.ConnectError as e:
        logger.error(
            f"Webhook connection error for notification {notification_id}: {e} "
            f"(attempt {retry_count + 1}/4)"
        )
        if retry_count >= 3:
            await _send_to_dead_letter_queue(
                notification_id, user_id, payload, f"Connection error: {e}"
            )
            return {"success": False, "error": "Connection error - sent to DLQ"}

        raise TaskiqRetry(
            delay=_calculate_retry_delay(retry_count),
            labels={"retry_count": retry_count + 1},
        ) from e

    except Exception as e:
        logger.error(
            f"Webhook delivery failed for notification {notification_id}: {e} "
            f"(attempt {retry_count + 1}/4)"
        )
        if retry_count >= 3:
            await _send_to_dead_letter_queue(
                notification_id, user_id, payload, f"Unexpected error: {e}"
            )
            return {"success": False, "error": f"Failed - sent to DLQ: {e}"}

        raise TaskiqRetry(
            delay=_calculate_retry_delay(retry_count),
            labels={"retry_count": retry_count + 1},
        ) from e


def _calculate_retry_delay(retry_count: int) -> int:
    """Calculate exponential backoff delay."""
    delays = [60, 300, 3600]
    if retry_count < len(delays):
        return delays[retry_count]
    return 3600


async def _send_to_dead_letter_queue(
    notification_id: int,
    user_id: int,
    payload: dict,
    error_reason: str,
) -> None:
    """Send failed webhook to dead letter queue."""
    from collections.abc import Awaitable
    from typing import cast

    from app.core import redis_service

    logger.error(f"Sending notification {notification_id} to DLQ. Reason: {error_reason}")

    if redis_service.is_available and redis_service.client:
        import json

        dlq_entry = {
            "notification_id": notification_id,
            "user_id": user_id,
            "payload": payload,
            "error": error_reason,
            "timestamp": payload.get("timestamp"),
        }
        await cast(
            Awaitable[int],
            redis_service.client.lpush("queue:webhooks:dlq", json.dumps(dlq_entry)),
        )


@broker.task(task_name="retry_dlq_webhooks")
async def retry_dlq_webhooks_task() -> dict[str, int | str]:
    """Periodic task to retry webhooks from dead letter queue."""
    from collections.abc import Awaitable
    from typing import cast

    from app.core import redis_service

    if not redis_service.is_available or not redis_service.client:
        return {"error": "Redis unavailable"}

    import json

    retried = 0
    failed = 0

    while True:
        dlq_entry_json = await cast(
            Awaitable[str | None], redis_service.client.rpop("queue:webhooks:dlq")
        )
        if not dlq_entry_json:
            break

        try:
            dlq_entry = json.loads(dlq_entry_json)

            await send_webhook_task.kiq(
                notification_id=dlq_entry["notification_id"],
                user_id=dlq_entry["user_id"],
                **dlq_entry["payload"],
            )
            retried += 1

        except Exception as e:
            logger.error(f"Failed to retry DLQ entry: {e}")
            await cast(
                Awaitable[int],
                redis_service.client.lpush("queue:webhooks:dlq", dlq_entry_json),
            )
            failed += 1

    logger.info(f"DLQ retry complete: {retried} retried, {failed} failed")
    return {"retried": retried, "failed": failed}
