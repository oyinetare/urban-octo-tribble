"""RAG (Retrieval-Augmented Generation) service."""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_settings
from app.models import Chunk, Document
from app.schemas.query import Citation
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """Service for RAG-based question answering."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        session: AsyncSession | None = None,
    ):
        """
        Initialize RAG service.

        Args:
            vector_store: Vector store for semantic search
            llm_service: LLM service for generation
            session: Database session
        """
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.session = session

    async def _retrieve_chunks(
        self,
        query: str,
        # user_id: int,
        document_id: int | None = None,
        max_chunks: int = 5,
        min_score: float = 0.6,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks using semantic search.

        Args:
            query: User's question
            user_id: Current user ID
            document_id: Optional specific document to search
            max_chunks: Maximum chunks to retrieve
            min_score: Minimum similarity score

        Returns:
            List of chunk dictionaries with metadata
        """
        if self.session is None:
            raise RuntimeError(
                "RAGService.session is not set. Are you calling this through the dependency?"
            )

        # Create a local reference that the type checker knows is not None
        # session: AsyncSession = self.session

        # Ensure model is loaded
        await self.embedding_service._ensure_model_loaded()

        # Generate embedding (offload CPU-bound task to thread)
        query_embedding = await asyncio.to_thread(self.embedding_service.embed_text, query)

        # Search with correct parameters
        search_results = await self.vector_store.search(
            query_embedding=query_embedding,
            document_id=document_id,
            limit=max_chunks,
            score_threshold=min_score,
        )

        # Fetch full chunk and document data
        chunks_with_metadata = []
        for result in search_results:
            # chunk_id = result["id"]
            # If search_results is a list of objects
            chunk_id = getattr(result, "id", result.get("id") if isinstance(result, dict) else None)

            # Get chunk from database
            chunk_stmt = select(Chunk).where(Chunk.id == chunk_id)
            chunk_result = await self.session.execute(chunk_stmt)
            chunk = chunk_result.scalar_one_or_none()

            if not chunk:
                continue

            # Get document
            doc_stmt = select(Document).where(Document.id == chunk.document_id)
            doc_result = await self.session.execute(doc_stmt)
            document = doc_result.scalar_one_or_none()

            if not document:
                continue

            chunks_with_metadata.append(
                {
                    "chunk_id": chunk.id,
                    "chunk_text": chunk.text,
                    "chunk_position": chunk.position,
                    "document_id": document.id,
                    "document_title": document.title,
                    "similarity_score": result["score"],
                }
            )

        return chunks_with_metadata

    def _build_context(self, chunks: list[dict[str, Any]]) -> str:
        """
        Build context string from retrieved chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."

        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {idx}] (Document: {chunk['document_title']}, "
                f"Position: {chunk['chunk_position']}, "
                f"Similarity: {chunk['similarity_score']:.2f})\n"
                f"{chunk['chunk_text']}\n"
            )

        return "\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build user prompt with context.

        Args:
            query: User's question
            context: Retrieved context

        Returns:
            Formatted prompt
        """
        return f"""Context:
{context}

Question: {query}

Please answer the question based on the provided context. Include citations using [Source N] format."""

    async def ask(
        self,
        query: str,
        # user_id: int,
        document_id: int | None = None,
        max_chunks: int = 5,
        min_score: float = 0.6,
    ) -> tuple[str, list[Citation], str, str, int | None]:
        """
        Answer a question using RAG.

        Args:
            query: User's question
            user_id: Current user ID
            document_id: Optional specific document
            max_chunks: Maximum chunks to use
            min_score: Minimum similarity score

        Returns:
            Tuple of (answer, citations, provider, model, tokens_used)
        """
        # Step 1: Retrieve relevant chunks
        chunks = await self._retrieve_chunks(
            query=query,
            # user_id=user_id,
            document_id=document_id,
            max_chunks=max_chunks,
            min_score=min_score,
        )

        if not chunks:
            # No relevant context found
            answer = (
                "I couldn't find any relevant information in your documents to answer this question. "
                "Please try rephrasing your question or ensure the relevant documents are uploaded."
            )
            return answer, [], "none", "none", None

        # Step 2: Build context and prompt
        context = self._build_context(chunks)
        user_prompt = self._build_prompt(query, context)

        # Step 3: Generate answer
        answer, provider, model, tokens = await self.llm_service.generate(
            system_prompt=settings.RAG_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Step 4: Build citations
        citations = [
            Citation(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                document_title=chunk["document_title"],
                chunk_position=chunk["chunk_position"],
                similarity_score=chunk["similarity_score"],
                text_preview=chunk["chunk_text"][:200] + "..."
                if len(chunk["chunk_text"]) > 200
                else chunk["chunk_text"],
            )
            for chunk in chunks
        ]

        return answer, citations, provider, model, tokens
