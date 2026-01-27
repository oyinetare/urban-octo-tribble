import logging

from app.celery_app import celery_app
from app.core import AsyncSessionLocal
from app.models import Document
from app.services.chunking import ChunkBuilder, ChunkRepository, chunker

logger = logging.getLogger(__name__)


# Keep the logic in services and the orchestration in the task.
@celery_app.task
async def chunk_document(document_id: int):
    async with AsyncSessionLocal() as session:
        # 1. Fetch document
        document = await session.get(Document, document_id)
        if not document:
            return

        repo = ChunkRepository(session)
        builder = ChunkBuilder().from_document(document).with_chunker(chunker)

        try:
            # Use a transaction block for atomicity
            async with session.begin():
                # 2. Cleanup old data - Remove existing chunks to allow idempotency
                await repo.delete_by_document(document_id)

                # 3. Generate new chunks
                chunks = await builder.build()

                # 4. Save
                await repo.create_chunks(chunks)

            # 5. Success - Proceed to embedding
            # embed_chunks.delay(document_id)

        except Exception as e:
            # The transaction automatically rolls back on error
            await session.rollback()
            # Log error here using app.core.logger
            raise e
