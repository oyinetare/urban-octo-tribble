import asyncio
import logging
from typing import Any

from celery import Task

from app.core import ProcessingStatus
from app.models import Document

logger = logging.getLogger(__name__)


# Thread-local event loop storage
_loop_storage = {}


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """
    Get or create an event loop for the current worker thread.

    Critical: This ensures each Celery worker thread has exactly one event loop
    that persists for the lifetime of the worker process.
    """
    import threading

    thread_id = threading.get_ident()

    if thread_id not in _loop_storage:
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            # Create new loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        _loop_storage[thread_id] = loop
        logger.info(f"Created/cached event loop for thread {thread_id}")

    return _loop_storage[thread_id]


def run_async(coro: Any) -> Any:
    """
    Run async code in the persistent worker event loop.

    This is the bridge between Celery's sync world and your async code.
    Unlike asyncio.run(), this does NOT close the loop after execution.
    """
    loop = get_worker_event_loop()
    return loop.run_until_complete(coro)


def get_async_session():
    """
    Create a new AsyncSession bound to the current worker's event loop.

    CRITICAL: We can't use a global AsyncSessionLocal because it gets bound
    to whatever event loop was active at import time. Instead, we need to
    create sessions dynamically within the correct loop context.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.core.database import engine

    # Create a sessionmaker bound to the current loop's context
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session_factory()


class ProcessingTask(Task):
    """Base task with error handling and logging"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _ = (task_id, kwargs, einfo)
        document_id = args[0]

        async def update_status_failed():
            # Use the session creator instead of global AsyncSessionLocal
            session = get_async_session()
            try:
                async with session:
                    document = await session.get(Document, document_id)
                    if document:
                        document.processing_status = ProcessingStatus.FAILED
                        document.processing_error = str(exc)
                        await session.commit()
            except Exception as e:
                logger.error(f"Failed to update document status: {e}")
                raise

        try:
            run_async(update_status_failed())
        except Exception as e:
            logger.error(f"Error in on_failure handler: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        _ = (retval, args, kwargs)
        logger.info(f"Task {task_id} completed successfully")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        _ = (args, kwargs, einfo)
        logger.warning(f"Task {task_id} retrying: {exc}")
