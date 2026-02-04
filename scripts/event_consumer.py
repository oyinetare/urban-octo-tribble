#!/usr/bin/env python3
"""
Standalone Event Consumer

This script consumes events from Redpanda and logs them.

Usage:
    python scripts/event_consumer.py

To run in Docker:
    docker-compose exec api python scripts/event_consumer.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.events.consumer import EventConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# EVENT HANDLERS
# ============================================================================


async def handle_document_uploaded(event_data: dict):
    """Handle document.uploaded event."""
    data = event_data.get("data", {})
    user_id = event_data.get("user_id")

    logger.info(
        f"📄 [UPLOADED] User {user_id} uploaded '{data.get('title')}' "
        f"({data.get('file_size')} bytes, {data.get('content_type')})"
    )


async def handle_document_processing_started(event_data: dict):
    """Handle document.processing_started event."""
    data = event_data.get("data", {})

    logger.info(
        f"⚙️  [PROCESSING] Document {data.get('document_id')} "
        f"started processing (task={data.get('task_id')})"
    )


async def handle_document_processed(event_data: dict):
    """Handle document.processed event."""
    data = event_data.get("data", {})

    logger.info(
        f"✅ [PROCESSED] Document {data.get('document_id')} "
        f"text extracted ({data.get('text_length')} chars in {data.get('extraction_time_ms')}ms)"
    )


async def handle_document_chunked(event_data: dict):
    """Handle document.chunked event."""
    data = event_data.get("data", {})

    logger.info(
        f"📦 [CHUNKED] Document {data.get('document_id')} "
        f"split into {data.get('chunks_count')} chunks "
        f"(avg size: {data.get('avg_chunk_size')} chars)"
    )


async def handle_document_embedded(event_data: dict):
    """Handle document.embedded event."""
    data = event_data.get("data", {})

    logger.info(
        f"🧠 [EMBEDDED] Document {data.get('document_id')} "
        f"generated {data.get('embeddings_count')} embeddings "
        f"in {data.get('embedding_time_ms')}ms"
    )


async def handle_document_completed(event_data: dict):
    """Handle document.completed event."""
    data = event_data.get("data", {})
    user_id = event_data.get("user_id")

    logger.info(
        f"🎉 [COMPLETED] Document {data.get('document_id')} fully processed "
        f"for user {user_id} (total: {data.get('total_processing_time_ms')}ms)"
    )


async def handle_document_failed(event_data: dict):
    """Handle document.failed event."""
    data = event_data.get("data", {})

    logger.error(
        f"❌ [FAILED] Document {data.get('document_id')} "
        f"failed at {data.get('failed_stage')}: {data.get('error_message')}"
    )


async def handle_document_deleted(event_data: dict):
    """Handle document.deleted event."""
    data = event_data.get("data", {})
    user_id = event_data.get("user_id")

    logger.info(
        f"🗑️  [DELETED] User {user_id} deleted document {data.get('document_id')} "
        f"('{data.get('title')}')"
    )


async def handle_query_executed(event_data: dict):
    """Handle query.executed event."""
    data = event_data.get("data", {})
    user_id = event_data.get("user_id")

    logger.info(
        f"🔍 [QUERY] User {user_id} executed query: '{data.get('query_text')[:50]}...' "
        f"({data.get('response_time_ms')}ms, {data.get('llm_provider')}, "
        f"tokens={data.get('tokens_used')}, cache_hit={data.get('cache_hit')})"
    )


async def handle_user_registered(event_data: dict):
    """Handle user.registered event."""
    data = event_data.get("data", {})

    logger.info(
        f"👤 [REGISTERED] New user: {data.get('username')} "
        f"(email={data.get('email')}, tier={data.get('tier')})"
    )


async def handle_user_login(event_data: dict):
    """Handle user.login event."""
    data = event_data.get("data", {})

    logger.info(f"🔐 [LOGIN] User {data.get('username')} logged in (tier={data.get('tier')})")


async def handle_user_logout(event_data: dict):
    """Handle user.logout event."""
    data = event_data.get("data", {})

    logger.info(
        f"🔐 [LOGOUT] User {data.get('username')} logged in (username={data.get('username')})"
    )


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run the event consumer."""
    logger.info("🚀 Starting event consumer...")
    logger.info(f"📡 Kafka bootstrap servers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"📋 Topics: {settings.KAFKA_EVENTS_TOPIC}, {settings.KAFKA_ANALYTICS_TOPIC}")
    logger.info(f"👥 Consumer group: {settings.KAFKA_CONSUMER_GROUP}")

    # Create consumer
    consumer = EventConsumer(
        topics=[
            settings.KAFKA_EVENTS_TOPIC,
            settings.KAFKA_ANALYTICS_TOPIC,
        ],
        group_id=settings.KAFKA_CONSUMER_GROUP,
    )

    # Register handlers
    consumer.register_handler("document.uploaded", handle_document_uploaded)
    consumer.register_handler("document.processing_started", handle_document_processing_started)
    consumer.register_handler("document.processed", handle_document_processed)
    consumer.register_handler("document.chunked", handle_document_chunked)
    consumer.register_handler("document.embedded", handle_document_embedded)
    consumer.register_handler("document.completed", handle_document_completed)
    consumer.register_handler("document.failed", handle_document_failed)
    consumer.register_handler("document.deleted", handle_document_deleted)
    consumer.register_handler("query.executed", handle_query_executed)
    consumer.register_handler("user.registered", handle_user_registered)
    consumer.register_handler("user.login", handle_user_login)
    consumer.register_handler("user.logout", handle_user_logout)

    # Start consumer
    try:
        await consumer.start()
        logger.info("✅ Consumer started successfully")
        logger.info("📨 Waiting for events... (Press Ctrl+C to stop)")

        # Consume events
        await consumer.consume()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Consumer error: {e}", exc_info=True)
    finally:
        await consumer.stop()
        logger.info("✅ Consumer stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
