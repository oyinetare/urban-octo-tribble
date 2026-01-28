import asyncio
import logging

from celery import shared_task

from app.core import AsyncSessionLocal, extraction_factory
from app.models import Document
from app.services import storage_service
from app.tasks import ProcessingTask

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
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

        from app.tasks.chunk_document import chunk_document

        chunk_document.delay(document_id)
        # chunk_document.apply_async(args=[document_id])

        # Success (100%)
        return {"document_id": document_id, "status": "success", "text_length": len(text)}
