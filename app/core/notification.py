import logging
from typing import Protocol

import httpx

from app.models import Notification

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    """Protocol for notification delivery channels."""

    async def send(self, notification: Notification) -> bool:
        """Send notification through this channel."""
        ...


class InAppChannel:
    """In-app notification channel (database storage)."""

    async def send(self, _notification: Notification) -> bool:
        """Notification is already saved to database."""
        return True


class WebhookChannel:
    """Webhook notification channel with task queue support."""

    def __init__(self, use_queue: bool = True):
        """
        Initialize webhook channel.

        Args:
            use_queue: If True, enqueue webhooks for background processing.
                      If False, send webhooks immediately (for testing).
        """
        self.use_queue = use_queue

    async def send(self, notification: Notification) -> bool:
        """Send notification via webhook (enqueue or send immediately)."""
        if self.use_queue:
            return await self._enqueue_webhook(notification)
        else:
            return await self._send_webhook_immediate(notification)

    async def _enqueue_webhook(self, notification: Notification) -> bool:
        """Enqueue webhook for background processing."""
        from app.core import redis_service

        if not redis_service.is_available:
            logger.warning("Redis unavailable, falling back to immediate webhook send")
            return await self._send_webhook_immediate(notification)

        try:
            # Prepare webhook payload
            payload = {
                "notification_id": notification.id,
                "user_id": notification.user_id,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "action_url": notification.action_url,
                "timestamp": notification.created_at.isoformat(),
                "retry_count": 0,
            }

            # Push to Redis queue
            await redis_service.enqueue_webhook(payload)
            logger.info(f"Enqueued webhook for notification {notification.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to enqueue webhook: {e}")
            # Fall back to immediate send
            return await self._send_webhook_immediate(notification)

    async def _send_webhook_immediate(self, notification: Notification) -> bool:
        """Send webhook immediately (blocking)."""
        from sqlmodel import select

        from app.dependencies import get_session
        from app.models import User

        # Get user's webhook URL
        async for session in get_session():
            statement = select(User).where(User.id == notification.user_id)
            result = await session.execute(statement)
            user = result.scalar_one_or_none()

            if not user or not user.webhook_url:
                logger.debug(f"No webhook URL for user {notification.user_id}")
                return False

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        user.webhook_url,
                        json={
                            "type": notification.type,
                            "title": notification.title,
                            "message": notification.message,
                            "action_url": notification.action_url,
                            "timestamp": notification.created_at.isoformat(),
                        },
                        timeout=5.0,
                    )
                    success = response.status_code == 200
                    if success:
                        logger.info(f"Webhook sent successfully for notification {notification.id}")
                    else:
                        logger.warning(
                            f"Webhook failed with status {response.status_code} "
                            f"for notification {notification.id}"
                        )
                    return success
            except httpx.TimeoutException:
                logger.error(f"Webhook timeout for notification {notification.id}")
                return False
            except Exception as e:
                logger.error(f"Webhook delivery failed for notification {notification.id}: {e}")
                return False

        return False


class NotificationService:
    """
    Service for managing notifications across multiple channels.

    NOT a singleton - instantiated once during app startup and managed
    via FastAPI's lifespan and dependency injection.
    """

    def __init__(self, use_webhook_queue: bool = True):
        """
        Initialize notification service.

        Args:
            use_webhook_queue: If True, use Redis queue for webhooks.
                              If False, send webhooks immediately.
        """
        self.channels: list[NotificationChannel] = [
            InAppChannel(),
            WebhookChannel(use_queue=use_webhook_queue),
        ]
        logger.info("NotificationService initialized")

    async def notify(self, notification: Notification) -> dict[str, bool]:
        """
        Send notification through all channels.

        Returns:
            Dict mapping channel names to success status
        """
        results = {}

        for channel in self.channels:
            channel_name = channel.__class__.__name__
            try:
                success = await channel.send(notification)
                results[channel_name] = success
                if not success:
                    logger.warning(
                        f"Channel {channel_name} failed for notification {notification.id}"
                    )
            except Exception as e:
                logger.error(
                    f"Channel {channel_name} raised exception for "
                    f"notification {notification.id}: {e}"
                )
                results[channel_name] = False

        return results


# Global notification service (managed by app lifecycle)
notification_service = NotificationService()
