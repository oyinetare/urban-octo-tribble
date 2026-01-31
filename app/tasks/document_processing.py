import logging

from celery import shared_task

from app.core import ProcessingStatus, extraction_factory
from app.models import Document
from app.services.storage import storage_service
from app.tasks import ProcessingTask
from app.tasks.base import get_async_session, run_async

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def process_document(self, document_id: int):
    return run_async(_async_process(self, document_id))


async def _async_process(self, document_id: int):
    # Create session in the task's event loop context
    session = get_async_session()

    async with session:
        # 1. Fetch & Validate
        self.update_state(state="PROGRESS", meta={"percent": 10, "step": "fetching"})
        document = await session.get(Document, document_id)

        if not document:
            raise ValueError(f"Document {document_id} not found.")

        # 2. Process
        self.update_state(state="PROGRESS", meta={"percent": 40, "step": "downloading"})
        content = await storage_service.download(document.storage_key)

        self.update_state(state="PROGRESS", meta={"percent": 70, "step": "extracting"})
        extractor = extraction_factory.get_extractor(document.content_type)
        text = await extractor.extract(content)

        # 3. Finalize DB
        self.update_state(state="PROGRESS", meta={"percent": 90, "step": "saving"})
        document.content = text
        document.processing_status = ProcessingStatus.COMPLETED
        await session.commit()

    # 4. Trigger Next Step (After commit and session close)
    from app.tasks.document_chunking import chunk_document

    chunk_document.delay(document_id)

    return {"document_id": document_id, "status": "success"}
