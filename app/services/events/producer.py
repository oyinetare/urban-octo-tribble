"""
Event Producer Service for publishing events to Kafka/Redpanda.

This service handles:
- Connection management to Kafka
- Event publishing with retry logic
- Error handling and logging
- Graceful shutdown
"""

import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import get_settings
from app.schemas.events import BaseEvent
from app.utility import id_generator, utc_now

logger = logging.getLogger(__name__)
settings = get_settings()


class EventProducer:
    """
    Async event producer for Kafka/Redpanda.

    Features:
    - Automatic reconnection on failure
    - Async publishing for non-blocking operations
    - JSON serialization of event schemas
    - Topic routing based on event type
    """

    def __init__(self):
        self.producer: AIOKafkaProducer | None = None
        self.is_initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize Kafka producer connection."""
        if not settings.KAFKA_ENABLE_EVENTS:
            logger.info("📊 Event publishing is DISABLED (KAFKA_ENABLE_EVENTS=False)")
            return

        async with self._lock:
            if self.is_initialized:
                return

            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    # Reliability settings
                    acks="all",  # Wait for all replicas
                    # Batching for performance
                    compression_type="gzip",
                    linger_ms=10,  # Wait 10ms to batch messages
                )

                await self.producer.start()
                self.is_initialized = True
                logger.info(f"✅ Event producer initialized: {settings.KAFKA_BOOTSTRAP_SERVERS}")

            except Exception as e:
                logger.error(f"❌ Failed to initialize event producer: {e}")
                self.producer = None
                self.is_initialized = False

    async def publish(self, event: BaseEvent, topic: str | None = None) -> bool:
        """
        Publish an event to Kafka.

        Args:
            event: Event schema to publish
            topic: Topic name (defaults to KAFKA_EVENTS_TOPIC)

        Returns:
            bool: True if published successfully, False otherwise
        """
        if not settings.KAFKA_ENABLE_EVENTS:
            logger.debug(f"Event publishing disabled: {event.event_type}")
            return False

        if not self.is_initialized or not self.producer:
            logger.warning("Event producer not initialized, attempting to initialize...")
            await self.initialize()

            if not self.producer:
                logger.error("Failed to initialize producer, event dropped")
                return False

        # Default topic
        if topic is None:
            topic = settings.KAFKA_EVENTS_TOPIC

        try:
            # Convert Pydantic model to dict
            event_data = event.model_dump(mode="json")

            # Publish to Kafka
            if self.producer is None:
                logger.error("Producer is None, event dropped")
                return False

            await self.producer.send_and_wait(
                topic=topic,
                value=event_data,
                key=str(event.event_id).encode("utf-8"),  # Use event_id as partition key
            )

            logger.debug(
                f"📤 Published event: {event.event_type} (id={event.event_id}) to topic '{topic}'"
            )
            return True

        except KafkaError as e:
            logger.error(f"❌ Kafka error publishing event {event.event_type}: {e}", exc_info=True)
            return False

        except Exception as e:
            logger.error(
                f"❌ Unexpected error publishing event {event.event_type}: {e}", exc_info=True
            )
            return False

    async def publish_analytics(self, event: BaseEvent) -> bool:
        """Publish event to analytics topic."""
        return await self.publish(event, topic=settings.KAFKA_ANALYTICS_TOPIC)

    async def close(self):
        """Gracefully close producer connection."""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("✅ Event producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")
            finally:
                self.producer = None
                self.is_initialized = False


# ============================================================================
# HELPER FUNCTIONS FOR CREATING EVENTS
# ============================================================================


def create_event(
    event_type: str, data: dict[str, Any], user_id: int | None = None
) -> dict[str, Any]:
    """
    Helper to create event payload.

    This is a simplified version if you don't want to use Pydantic schemas.
    """
    return {
        "event_type": event_type,
        "event_id": id_generator.generate(),
        "timestamp": utc_now().isoformat(),
        "user_id": user_id,
        "data": data,
    }


# Global producer instance
event_producer = EventProducer()
