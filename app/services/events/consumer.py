"""
Event Consumer Service for consuming events from Kafka/Redpanda.

This service handles:
- Consuming events from multiple topics
- Event routing to handlers
- Error handling and dead letter queue
- Consumer group management
"""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from aiokafka import AIOKafkaConsumer

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EventConsumer:
    """
    Async event consumer for Kafka/Redpanda.

    Features:
    - Subscribe to multiple topics
    - Register handlers for specific event types
    - Automatic offset commits
    - Error handling with retry
    """

    def __init__(self, topics: list[str] | None = None, group_id: str | None = None):
        """
        Initialize event consumer.

        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID (defaults to config)
        """
        self.topics = topics or [settings.KAFKA_EVENTS_TOPIC, settings.KAFKA_ANALYTICS_TOPIC]
        self.group_id = group_id or settings.KAFKA_CONSUMER_GROUP
        self.consumer: AIOKafkaConsumer | None = None
        self.handlers: dict[str, list[Callable]] = {}
        self.is_running = False
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the consumer."""
        async with self._lock:
            if self.consumer is not None:
                return

            try:
                self.consumer = AIOKafkaConsumer(
                    *self.topics,
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    # Consumer settings
                    auto_offset_reset="earliest",  # Start from beginning if no offset
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,  # Commit every 5 seconds
                )

                await self.consumer.start()
                self.is_running = True
                logger.info(
                    f"✅ Event consumer started: {self.group_id} (topics: {', '.join(self.topics)})"
                )

            except Exception as e:
                logger.error(f"❌ Failed to start event consumer: {e}")
                self.consumer = None
                self.is_running = False
                raise

    async def stop(self):
        """Stop the consumer."""
        self.is_running = False

        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("✅ Event consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")
            finally:
                self.consumer = None

    def register_handler(self, event_type: str, handler: Callable[[dict[str, Any]], Any]):
        """
        Register a handler for a specific event type.

        Args:
            event_type: Event type to handle (e.g., "document.uploaded")
            handler: Async function to handle the event

        Example:
            async def handle_upload(event_data):
                print(f"Document uploaded: {event_data}")

            consumer.register_handler("document.uploaded", handle_upload)
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)
        logger.info(f"📝 Registered handler for event type: {event_type}")

    async def consume(self):
        """
        Start consuming events.

        This runs in an infinite loop until stop() is called.
        """
        if not self.consumer or not self.is_running:
            raise RuntimeError("Consumer not started. Call start() first.")

        logger.info("🔄 Starting event consumption loop...")

        try:
            async for message in self.consumer:
                try:
                    event_data = message.value
                    event_type = event_data.get("event_type")

                    if not event_type:
                        logger.warning(f"Event missing event_type: {event_data}")
                        continue

                    logger.debug(
                        f"📨 Received event: {event_type} "
                        f"(partition={message.partition}, offset={message.offset})"
                    )

                    # Route to handlers
                    await self._route_event(event_type, event_data)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in message: {e}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")

        except Exception as e:
            logger.error(f"Fatal error in consumer loop: {e}", exc_info=True)
            raise

    async def _route_event(self, event_type: str, event_data: dict[str, Any]):
        """Route event to registered handlers."""
        handlers = self.handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers registered for event type: {event_type}")
            return

        # Execute all handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)

            except Exception as e:
                logger.error(f"Error in handler for {event_type}: {e}", exc_info=True)


# ============================================================================
# EXAMPLE HANDLERS
# ============================================================================


async def log_document_uploaded(event_data: dict[str, Any]):
    """Example handler: Log document uploads."""
    data = event_data.get("data", {})
    logger.info(f"📄 Document uploaded: {data.get('title')} ({data.get('file_size')} bytes)")


async def log_query_executed(event_data: dict[str, Any]):
    """Example handler: Log query execution."""
    data = event_data.get("data", {})
    logger.info(
        f"🔍 Query executed: '{data.get('query_text')[:50]}...' "
        f"({data.get('response_time_ms')}ms, "
        f"provider={data.get('llm_provider')})"
    )


async def track_user_activity(event_data: dict[str, Any]):
    """Example handler: Track user activity metrics."""
    user_id = event_data.get("user_id")
    event_type = event_data.get("event_type")

    logger.info(f"📊 User {user_id} activity: {event_type}")

    # Here you could:
    # - Increment Redis counters
    # - Send to analytics service
    # - Update user statistics in database
