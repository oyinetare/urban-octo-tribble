# import logging
# from collections.abc import Awaitable
# from typing import cast

# logger = logging.getLogger(__name__)

# def _calculate_retry_delay(retry_count: int) -> int:
#     """
#     Calculate exponential backoff delay.

#     Retry schedule:
#     - Retry 1: 60 seconds (1 minute)
#     - Retry 2: 300 seconds (5 minutes)
#     - Retry 3: 3600 seconds (1 hour)

#     Args:
#         retry_count: Current retry count (0-indexed)

#     Returns:
#         Delay in seconds
#     """
#     delays = [60, 300, 3600]  # 1m, 5m, 1h
#     if retry_count < len(delays):
#         return delays[retry_count]
#     return 3600  # Default to 1 hour for any additional retries


# async def _send_to_dead_letter_queue(
#     notification_id: int,
#     user_id: int,
#     payload: dict,
#     error_reason: str,
# ) -> None:
#     """
#     Send failed webhook to dead letter queue.

#     Options for DLQ:
#     1. Store in separate Redis list for manual review
#     2. Store in database with 'failed' status
#     3. Send alert to admin

#     Args:
#         notification_id: ID of failed notification
#         user_id: User ID
#         payload: Webhook payload
#         error_reason: Reason for failure
#     """
#     from app.core import redis_service

#     logger.error(
#         f"Sending notification {notification_id} to DLQ. Reason: {error_reason}"
#     )

#     # Option 1: Store in Redis DLQ
#     if redis_service.is_available:
#         import json

#         dlq_entry = {
#             "notification_id": notification_id,
#             "user_id": user_id,
#             "payload": payload,
#             "error": error_reason,
#             "timestamp": payload.get("timestamp"),
#         }
#         await cast( Awaitable[int], redis_service.client.lpush(
#             "queue:webhooks:dlq", json.dumps(dlq_entry)
#         ))

#     # Option 2: Update notification status in database
#     # async with session_factory() as session:
#     #     notification = await session.get(Notification, notification_id)
#     #     if notification:
#     #         notification.delivery_status = "failed"
#     #         notification.delivery_error = error_reason
#     #         await session.commit()

#     # Option 3: Send alert (future implementation)
#     # await send_admin_alert(f"Webhook DLQ: notification {notification_id}")
