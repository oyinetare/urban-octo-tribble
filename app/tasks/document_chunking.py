import logging

from celery import shared_task

from app.core import ProcessingStatus
from app.models import Document
from app.services import ChunkBuilder, ChunkRepository, chunker
from app.tasks import ProcessingTask
from app.tasks.base import get_async_session, run_async

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def chunk_document(self, document_id: int):
    return run_async(_async_chunking(self, document_id))


async def _async_chunking(self, document_id: int):
    # Create session in the task's event loop context
    session = get_async_session()

    async with session:
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found.")

        repo = ChunkRepository(session)
        builder = ChunkBuilder().from_document(document).with_chunker(chunker)

        try:
            # 1. Clear old data and 2. Generate new
            await repo.delete_by_document(document_id)
            chunks = await builder.build()

            # 3. Save & Commit
            await repo.create_chunks(chunks)

            # Update status before closing session
            document.processing_status = ProcessingStatus.COMPLETED
            await session.commit()

        except Exception as e:
            await session.rollback()
            raise e

    # 4. Chain to next task AFTER session is closed and committed
    from app.tasks.chunks_embedding import embed_chunks

    embed_chunks.delay(document_id)

    return {"document_id": document_id, "status": "success", "chunks_count": len(chunks)}
