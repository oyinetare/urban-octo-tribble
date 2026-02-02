import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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

        # Ensure model is loaded
        await self.embedding_service._ensure_model_loaded()

        # Generate embedding (offload CPU-bound task to thread)
        query_embedding = await asyncio.to_thread(self.embedding_service.embed_text, query)

        # Search Qdrant
        search_results = await self.vector_store.search(
            query_embedding=query_embedding,
            document_id=document_id,
            limit=max_chunks,
            score_threshold=min_score,
        )

        logger.info(f"🔍 Vector search returned {len(search_results)} results")

        # Use data from Qdrant payload directly (now includes chunk_id!)
        chunks_with_metadata = []
        for result in search_results:
            chunks_with_metadata.append(
                {
                    "chunk_id": result.get("chunk_id"),  # Now populated from payload
                    "chunk_text": result.get("chunk_text", ""),
                    "chunk_position": result.get("chunk_index", 0),
                    "document_id": result.get("document_id"),
                    "document_title": result.get("metadata", {}).get("document_title", "Unknown"),
                    "similarity_score": result.get("score", 0.0),
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
        document_id: int | None = None,
        max_chunks: int = 5,
        min_score: float = 0.6,
    ) -> tuple[str, list[Citation], str, str, int | None]:
        """
        Answer a question using RAG.

        Args:
            query: User's question
            document_id: Optional specific document
            max_chunks: Maximum chunks to use
            min_score: Minimum similarity score

        Returns:
            Tuple of (answer, citations, provider, model, tokens_used)
        """
        # Step 1: Retrieve relevant chunks
        chunks = await self._retrieve_chunks(
            query=query,
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
                chunk_id=chunk.get("chunk_id"),  # Use .get() to safely handle None
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

    async def ask_stream(
        self,
        query: str,
        document_id: int | None = None,
        max_chunks: int = 5,
        min_score: float = 0.6,
    ):
        """
        Answer a question using RAG with streaming response.

        Args:
            query: User's question
            document_id: Optional specific document
            max_chunks: Maximum chunks to use
            min_score: Minimum similarity score

        Yields:
            dict: Event data with different types:
                - type: 'citations' - Initial citations before streaming starts
                - type: 'token' - Individual text tokens
                - type: 'usage' - Token usage statistics
                - type: 'error' - Error information
        """
        # Step 1: Retrieve relevant chunks
        chunks = await self._retrieve_chunks(
            query=query,
            document_id=document_id,
            max_chunks=max_chunks,
            min_score=min_score,
        )

        if not chunks:
            # No relevant context found
            yield {
                "type": "token",
                "data": "I couldn't find any relevant information in your documents to answer this question. "
                "Please try rephrasing your question or ensure the relevant documents are uploaded.",
                "provider": "none",
                "model": "none",
            }
            yield {
                "type": "citations",
                "data": [],
                "provider": "none",
                "model": "none",
            }
            return

        # Step 2: Build citations and send them first
        citations = [
            Citation(
                chunk_id=chunk.get("chunk_id"),
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

        # Send citations as first event
        yield {
            "type": "citations",
            "data": [citation.model_dump() for citation in citations],
        }

        # Step 3: Build context and prompt
        context = self._build_context(chunks)
        user_prompt = self._build_prompt(query, context)

        # Step 4: Stream the answer
        async for event in self.llm_service.generate_stream(
            system_prompt=settings.RAG_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        ):
            yield event
