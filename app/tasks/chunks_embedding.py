import logging
import time

from celery import shared_task

from app.core import ProcessingStatus, services
from app.models import Document
from app.schemas.events import (
    DocumentCompletedData,
    DocumentCompletedEvent,
    DocumentEmbeddedData,
    DocumentEmbeddedEvent,
)
from app.tasks.base import get_async_session, run_async
from app.tasks.document_processing import ProcessingTask
from app.utility import id_generator, utc_now

logger = logging.getLogger(__name__)


@shared_task(base=ProcessingTask, bind=True)
def embed_chunks(self, document_id: int):
    return run_async(_async_embedding(self, document_id))


async def _async_embedding(self, document_id: int):
    start_time = time.time()

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

        # Get chunks
        from typing import Any, cast

        from sqlalchemy import select

        from app.models import Chunk

        stmt = (
            select(Chunk)
            .where(cast(Any, Chunk.document_id == document_id))
            .order_by(cast(Any, Chunk.position))
        )
        result = await session.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks:
            document.processing_status = ProcessingStatus.COMPLETED
            await session.commit()
            return {"document_id": document_id, "status": "no_chunks"}

        # Generate embeddings (CPU-bound, runs in thread pool)
        self.update_state(state="PROGRESS", meta={"step": "generating_embeddings"})
        embeddings = embedding_service.embed_batch(texts=[c.text for c in chunks], batch_size=32)

        # Store in vector database with chunk IDs
        self.update_state(state="PROGRESS", meta={"step": "indexing_vectors"})
        # Store each chunk individually with its database ID
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            await vector_store.add_document_chunk(
                chunk_id=chunk.id,
                document_id=document_id,
                chunk_text=chunk.text,
                chunk_index=chunk.position,
                embedding=embedding,
                metadata={
                    "document_title": document.title,
                    "user_id": document.owner_id,
                },
            )

        embedding_time_ms = int((time.time() - start_time) * 1000)

        # Mark as completed
        document.processing_status = ProcessingStatus.COMPLETED
        await session.commit()

        #  PUBLISH EVENT: Embedding completed
        if services.events:
            event = DocumentEmbeddedEvent(
                event_id=id_generator.generate(),
                timestamp=utc_now(),
                user_id=document.owner_id,
                data=DocumentEmbeddedData(
                    document_id=document_id,
                    embeddings_count=len(embeddings),
                    embedding_time_ms=embedding_time_ms,
                ),
            )
            await services.events.publish(event)

        #  PUBLISH EVENT: Document fully completed
        if services.events:
            # Calculate total processing time (approximate)
            total_time_ms = embedding_time_ms  # You could track this better

            event = DocumentCompletedEvent(
                event_id=id_generator.generate(),
                timestamp=utc_now(),
                user_id=document.owner_id,
                data=DocumentCompletedData(
                    document_id=document_id,
                    total_processing_time_ms=total_time_ms,
                ),
            )
            await services.events.publish(event)

    return {"document_id": document_id, "chunks": len(chunks)}
