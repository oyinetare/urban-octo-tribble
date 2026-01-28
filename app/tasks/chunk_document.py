import asyncio
import logging

from celery import shared_task

from app.core import AsyncSessionLocal
from app.models import Document
from app.services import ChunkBuilder, ChunkRepository, chunker
from app.tasks import ProcessingTask

logger = logging.getLogger(__name__)


# Keep the logic in services and the orchestration in the task.
@shared_task(base=ProcessingTask, bind=True)
def chunk_document(self, document_id: int):
    # Use the base class logic; bridge sync celery to async logic
    return asyncio.run(_async_chunking(self, document_id))


async def _async_chunking(self, document_id: int):
    async with AsyncSessionLocal() as session:
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
            document.processing_status = "chunked"
            await session.commit()

        except Exception as e:
            await session.rollback()
            # Your ProcessingTask base class handles the DB "failed" status update
            raise e

    # 4. Chain to next task AFTER session is closed and committed
    from app.tasks.chunks_embedding import embed_chunks

    embed_chunks.delay(document_id)

    return {"document_id": document_id, "status": "success", "chunks_count": len(chunks)}
