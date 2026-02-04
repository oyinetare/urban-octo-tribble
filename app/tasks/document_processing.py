# app/tasks/document_processing.py (Updated with Events)

import logging
import time

from celery import shared_task

from app.core import ProcessingStatus, extraction_factory, services
from app.models import Document
from app.schemas.events import (
    DocumentFailedData,
    DocumentFailedEvent,
    DocumentProcessedData,
    DocumentProcessedEvent,
    DocumentProcessingStartedData,
    DocumentProcessingStartedEvent,
)
from app.tasks import ProcessingTask
from app.tasks.base import get_async_session, run_async
from app.utility import id_generator, utc_now

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def process_document(self, document_id: int):
    return run_async(_async_process(self, document_id))


async def _async_process(self, document_id: int):
    start_time = time.time()
    session = get_async_session()

    async with session:
        # 1. Fetch & Validate
        self.update_state(state="PROGRESS", meta={"percent": 10, "step": "fetching"})
        document = await session.get(Document, document_id)

        if not document:
            raise ValueError(f"Document {document_id} not found.")

        #  PUBLISH EVENT: Processing started
        if services.events:
            event = DocumentProcessingStartedEvent(
                event_id=id_generator.generate(),
                timestamp=utc_now(),
                user_id=document.owner_id,
                data=DocumentProcessingStartedData(
                    document_id=document_id,
                    task_id=self.request.id,
                ),
            )
            await services.events.publish(event)

        try:
            # 2. Download from storage
            self.update_state(state="PROGRESS", meta={"percent": 40, "step": "downloading"})

            # Initialize storage service if needed
            if not services.storage:
                await services.init()

            content = await services.storage.download(document.storage_key)

            # 3. Extract text
            self.update_state(state="PROGRESS", meta={"percent": 70, "step": "extracting"})
            extractor = extraction_factory.get_extractor(document.content_type)
            text = await extractor.extract(content)

            extraction_time_ms = int((time.time() - start_time) * 1000)

            # 4. Save to database
            self.update_state(state="PROGRESS", meta={"percent": 90, "step": "saving"})
            document.content = text
            document.processing_status = ProcessingStatus.COMPLETED
            await session.commit()

            #  PUBLISH EVENT: Processing completed
            if services.events:
                event = DocumentProcessedEvent(
                    event_id=id_generator.generate(),
                    timestamp=utc_now(),
                    user_id=document.owner_id,
                    data=DocumentProcessedData(
                        document_id=document_id,
                        text_length=len(text),
                        extraction_time_ms=extraction_time_ms,
                    ),
                )
                await services.events.publish(event)

        except Exception as e:
            # Mark as failed
            document.processing_status = ProcessingStatus.FAILED
            document.processing_error = str(e)
            await session.commit()

            #  PUBLISH EVENT: Processing failed
            if services.events:
                event = DocumentFailedEvent(
                    event_id=id_generator.generate(),
                    timestamp=utc_now(),
                    user_id=document.owner_id,
                    data=DocumentFailedData(
                        document_id=document_id,
                        error_message=str(e),
                        failed_stage="extraction",
                    ),
                )
                await services.events.publish(event)

            raise

    # 5. Chain to next task
    from app.tasks.document_chunking import chunk_document

    chunk_document.delay(document_id)

    return {"document_id": document_id, "status": "success"}
