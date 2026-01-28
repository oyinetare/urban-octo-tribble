import asyncio
import logging
from typing import Any, cast

from celery import shared_task

from app.core import AsyncSessionLocal, services
from app.models import Chunk, Document
from app.tasks import ProcessingTask

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def embed_chunks(self, document_id: int):
    # Use the base class logic; bridge sync celery to async logic
    return asyncio.run(_async_embedding(self, document_id))


async def _async_embedding(self, document_id: int):
    # 1. Initialize and capture local references
    await services.init()
    embedding_service = services.embedding
    vector_store = services.vector_store

    # 2. Type Guard: This "narrows" the types for the rest of the function
    if embedding_service is None or vector_store is None:
        logger.error("Embedding or Vector Store service failed to initialize")
        raise RuntimeError("Required services are unavailable")

    async with AsyncSessionLocal() as session:
        # 1. Fetch
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # 2. Get Chunks
        from sqlalchemy import select

        stmt = (
            select(Chunk)
            .where(cast(Any, Chunk.document_id == document_id))
            .order_by(cast(Any, Chunk.position))
        )

        result = await session.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            document.processing_status = "completed"
            await session.commit()
            return {"document_id": document_id, "status": "no_chunks"}

        # 3. Embed (Now safe because of the Type Guard above)
        self.update_state(state="PROGRESS", meta={"step": "generating_embeddings"})
        embeddings = embedding_service.embed_batch(texts=[c.text for c in chunks], batch_size=32)

        # 4. Vector Store Sync (Now safe because of the Type Guard above)
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

        # 5. Finalize
        document.processing_status = "completed"
        await session.commit()

    return {"document_id": document_id, "chunks": len(chunks)}
