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
    # Standard loop handling
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the task logic in the process-level loop
    # Pass 'self' so the async function can update status
    return loop.run_until_complete(_async_chunking(self, document_id))


async def _async_chunking(self, document_id: int):
    async with AsyncSessionLocal() as session:
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found.")

        repo = ChunkRepository(session)
        builder = ChunkBuilder().from_document(document).with_chunker(chunker)

        try:
            # 1. Cleanup & 2. Generate chunks
            await repo.delete_by_document(document_id)
            chunks = await builder.build()

            # 3. Save & Manual Commit
            await repo.create_chunks(chunks)
            await session.commit()  # Explicitly commit instead of using session.begin()

        except Exception as e:
            await session.rollback()
            raise e
