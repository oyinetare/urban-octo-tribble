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
    # Standard loop handling
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the task logic in the process-level loop
    # Pass 'self' so the async function can update status
    return loop.run_until_complete(_async_process(self, document_id))


async def _async_process(self, document_id: int):
    async with AsyncSessionLocal() as session:
        # 1. Start (10%) Get document and explicitly check for None
        self.update_state(state="PROGRESS", meta={"percent": 10, "step": "fetching"})
        document = await session.get(Document, document_id)

        if document is None:
            # This error message flows to on_failure automatically
            raise ValueError(f"Document {document_id} not found.")

        # 2. Download (40%) Safely access attributes now that we know 'document' exists
        self.update_state(state="PROGRESS", meta={"percent": 40, "step": "downloading"})
        content = await storage_service.download(document.storage_key)

        # 3. Extract (70%)
        self.update_state(state="PROGRESS", meta={"percent": 70, "step": "extracting"})
        extractor = extraction_factory.get_extractor(document.content_type)
        text = await extractor.extract(content)

        # 4. Save (90%) Update and commit
        self.update_state(state="PROGRESS", meta={"percent": 90, "step": "saving"})
        document.content = text
        document.processing_status = "completed"
        await session.commit()

        # Success (100%)
        return {"document_id": document_id, "status": "success", "text_length": len(text)}
