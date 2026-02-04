# import logging

# from app.services.events import EventConsumer

# logger = logging.getLogger(__name__)

# consumer = EventConsumer()


# @consumer.register_handler("query.executed")
# async def track_query_stats(event):
#     """Track query statistics"""
#     # Simple metrics
#     await redis.incr("queries:total")
#     await redis.incr(f"queries:{date.today()}")

#     # Track popular queries
#     await redis.zincrby("queries:popular", 1, event.data.query_text[:100])

#     # Track performance
#     await redis.lpush("queries:response_times", event.data.response_time_ms)

#     logger.info(f"📊 Query tracked: {event.data.query_text[:50]}...")


# @consumer.register_handler("document.uploaded")
# async def track_upload_stats(event):
#     """Track upload statistics"""
#     await redis.incr("uploads:total")
#     await redis.incr(f"uploads:user:{event.user_id}")

#     logger.info(f"📄 Upload tracked: {event.data.title}")


# # Run consumer
# if __name__ == "__main__":
#     asyncio.run(consumer.consume())
