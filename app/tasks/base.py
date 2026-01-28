import asyncio
import logging

from asgiref.sync import async_to_sync
from celery import Task

from app.core import AsyncSessionLocal
from app.models import Document

logger = logging.getLogger(__name__)


class ProcessingTask(Task):
    """Base task with error handling and logging"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Use underscore for unused vars to pass Ruff ARG002
        _ = (task_id, kwargs, einfo)
        document_id = args[0]

        # Define the async cleanup logic
        async def update_status_failed():
            # Use a fresh session here to avoid any 'loop-attached' objects from the failed task
            async with AsyncSessionLocal() as session:
                document = await session.get(Document, document_id)
                if document:
                    document.processing_status = "failed"
                    document.processing_error = str(exc)
                    await session.commit()

        try:
            # Check if we are already in an async loop (Tests)
            loop = asyncio.get_running_loop()
            loop.create_task(update_status_failed())
        except RuntimeError:
            # No loop running (Standard Celery Worker)
            async_to_sync(update_status_failed)()

    def on_success(self, retval, task_id, args, kwargs):
        # Use underscore for unused vars to pass Ruff ARG002
        _ = (retval, args, kwargs)
        logger.info(f"Task {task_id} completed successfully")

    # Correct order: self, exc, task_id, args, kwargs, einfo
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        _ = (args, kwargs, einfo)
        logger.warning(f"Task {task_id} retrying: {exc}")
