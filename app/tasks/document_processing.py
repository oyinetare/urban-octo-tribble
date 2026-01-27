import asyncio
import logging

from celery import Task

from app.celery_app import celery_app
from app.core import AsyncSessionLocal, extraction_factory
from app.models import Document
from app.services import storage_service

logger = logging.getLogger(__name__)


class ProcessingTask(Task):
    """Base task with error handling and logging"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Use underscore for unused vars to pass Ruff ARG002
        _ = (task_id, kwargs, einfo)
        document_id = args[0]

        # Define the async cleanup logic
        async def update_status_failed():
            async with AsyncSessionLocal() as session:
                document = await session.get(Document, document_id)
                if document:
                    document.processing_status = "failed"
                    document.processing_error = str(exc)
                    await session.commit()

        # Run the async logic from this sync context
        try:
            asyncio.run(update_status_failed())
        except Exception as e:
            logger.error(f"Failed to update error status for doc {document_id}: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        # Use underscore for unused vars to pass Ruff ARG002
        _ = (retval, args, kwargs)
        logger.info(f"Task {task_id} completed successfully")

    # Correct order: self, exc, task_id, args, kwargs, einfo
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        _ = (args, kwargs, einfo)
        logger.warning(f"Task {task_id} retrying: {exc}")


@celery_app.task(base=ProcessingTask, bind=True)
def process_document(self, document_id: int):
    # Get the current loop for this worker process
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the task logic in the process-level loop
    return loop.run_until_complete(_async_process(document_id))


async def _async_process(document_id: int):
    async with AsyncSessionLocal() as session:
        # from app.core.database import engine
        # 1. Get document and explicitly check for None
        document = await session.get(Document, document_id)

        if document is None:
            # Raising an error here will trigger on_failure in ProcessingTask
            raise ValueError(f"Document with ID {document_id} not found in database.")

        # 2. Safely access attributes now that we know 'document' exists
        content = await storage_service.download(document.storage_key)

        # 3. Extract text
        extractor = extraction_factory.get_extractor(document.content_type)
        text = await extractor.extract(content)

        # 4. Update and commit
        document.content = text
        document.processing_status = "completed"
        await session.commit()

        return {"document_id": document_id, "status": "success"}
