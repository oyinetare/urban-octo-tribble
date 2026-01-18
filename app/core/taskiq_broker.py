"""
TaskIQ broker configuration with Redis backend.

This creates a shared TaskIQ broker instance that:
- Uses Redis as the message broker
- Supports async task execution
- Handles retries automatically
- Provides result backend for tracking task status
"""

from taskiq import TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.config import get_settings

settings = get_settings()

# ============================================================================
# REDIS BROKER SETUP
# ============================================================================

# Redis connection URL
redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"

# Create result backend (stores task results)
result_backend = RedisAsyncResultBackend(redis_url)

# Create broker with result backend
broker = ListQueueBroker(
    url=redis_url,
    result_backend=result_backend,
    queue_name="taskiq:main",  # Main task queue
    max_connection_pool_size=50,
)


# ============================================================================
# BROKER LIFECYCLE HOOKS
# ============================================================================


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def worker_startup(state: TaskiqState) -> None:
    """
    Initialize resources when worker starts.

    This runs once per worker process.
    """
    print("🚀 TaskIQ worker started")
    print(f"   Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print("   Queue: taskiq:main")

    # Import database connection here to avoid circular imports
    from app.core import AsyncSessionLocal

    # Store session factory in worker state (accessible in tasks)
    state.session_factory = AsyncSessionLocal


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def worker_shutdown(state: TaskiqState) -> None:
    """
    Cleanup resources when worker shuts down.
    """
    print("🛑 TaskIQ worker shutting down")


# ============================================================================
# TASK DECORATORS
# ============================================================================

# For tasks that need retries
task_with_retries = broker.task(
    retry_on_error=True,
    max_retries=3,
    retry_delay=60,  # Will be overridden by exponential backoff in task
)

# For tasks that should never retry
task_no_retry = broker.task(
    retry_on_error=False,
)
