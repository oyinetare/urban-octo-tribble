import logging
from typing import Any, cast

from celery import shared_task
from sqlalchemy import select

from app.core import ProcessingStatus, services
from app.models import Chunk, Document
from app.tasks import ProcessingTask
from app.tasks.base import get_async_session, run_async

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def embed_chunks(self, document_id: int):
    return run_async(_async_embedding(self, document_id))


async def _async_embedding(self, document_id: int):
    # 1. Initialize services (once per task is fine)
    await services.init()
    embedding_service = services.embedding
    vector_store = services.vector_store

    # 2. Type Guard
    if embedding_service is None or vector_store is None:
        logger.error("Embedding or Vector Store service failed to initialize")
        raise RuntimeError("Required services are unavailable")

    # 3. Create session in the task's event loop context
    session = get_async_session()

    async with session:
        # Fetch document
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Get Chunks
        stmt = (
            select(Chunk)
            .where(cast(Any, Chunk.document_id == document_id))
            .order_by(cast(Any, Chunk.position))
        )

        result = await session.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            document.processing_status = ProcessingStatus.COMPLETED
            await session.commit()
            return {"document_id": document_id, "status": "no_chunks"}

        # 4. Generate embeddings (CPU-bound, runs in thread pool)
        self.update_state(state="PROGRESS", meta={"step": "generating_embeddings"})
        embeddings = embedding_service.embed_batch(texts=[c.text for c in chunks], batch_size=32)

        # 5. Store in vector database
        self.update_state(state="PROGRESS", meta={"step": "indexing_vectors"})
        await vector_store.add_documents(
            document_id=document_id,
            chunks=[c.text for c in chunks],
            embeddings=embeddings,
            metadata={
                "document_title": document.title,
                "user_id": document.owner_id,
            },
        )

        # 6. Finalize
        document.processing_status = ProcessingStatus.COMPLETED
        await session.commit()

    return {"document_id": document_id, "chunks": len(chunks)}
