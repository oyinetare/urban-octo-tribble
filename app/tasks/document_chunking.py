import logging

from celery import shared_task

from app.core import ProcessingStatus, services
from app.models import Document
from app.schemas.events import (
    DocumentChunkedData,
    DocumentChunkedEvent,
    DocumentFailedData,
    DocumentFailedEvent,
)
from app.tasks.base import get_async_session, run_async
from app.tasks.document_processing import ProcessingTask
from app.utility import id_generator, utc_now

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def chunk_document(self, document_id: int):
    return run_async(_async_chunking(self, document_id))


async def _async_chunking(self, document_id: int):
    from app.services.ai import ChunkBuilder, ChunkRepository, chunker

    session = get_async_session()

    async with session:
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found.")

        repo = ChunkRepository(session)
        builder = ChunkBuilder().from_document(document).with_chunker(chunker)

        try:
            await repo.delete_by_document(document_id)
            chunks = await builder.build()
            await repo.create_chunks(chunks)

            document.processing_status = ProcessingStatus.COMPLETED
            await session.commit()

            #  PUBLISH EVENT: Chunking completed
            if services.events:
                avg_chunk_size = sum(len(c.text) for c in chunks) // len(chunks) if chunks else 0

                event = DocumentChunkedEvent(
                    event_id=id_generator.generate(),
                    timestamp=utc_now(),
                    user_id=document.owner_id,
                    data=DocumentChunkedData(
                        document_id=document_id,
                        chunks_count=len(chunks),
                        avg_chunk_size=avg_chunk_size,
                    ),
                )
                await services.events.publish(event)

        except Exception as e:
            await session.rollback()

            # Publish failure event
            if services.events:
                event = DocumentFailedEvent(
                    event_id=id_generator.generate(),
                    timestamp=utc_now(),
                    user_id=document.owner_id,
                    data=DocumentFailedData(
                        document_id=document_id,
                        error_message=str(e),
                        failed_stage="chunking",
                    ),
                )
                await services.events.publish(event)

            raise

    # Chain to embedding
    from app.tasks.chunks_embedding import embed_chunks

    embed_chunks.delay(document_id)

    return {"document_id": document_id, "status": "success", "chunks_count": len(chunks)}
