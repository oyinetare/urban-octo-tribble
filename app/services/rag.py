"""
RAG Service with Production Optimizations:
- Response caching (Redis)
- Embedding caching
- Query classification for smart routing
- Performance metrics tracking
- Score filtering
"""

import asyncio
import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.schemas.query import Citation
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.metrics_service import MetricsService
from app.services.query_classifier import QueryClassifier
from app.services.redis_service import RedisService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """Service for RAG-based question answering with production optimizations."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        session: AsyncSession | None = None,
        redis: RedisService | None = None,
        metrics_service: MetricsService | None = None,
        classifier: QueryClassifier | None = None,
    ):
        """
        Initialize RAG service.

        Args:
            vector_store: Vector store for semantic search
            llm_service: LLM service for generation
            embedding_service: Service for generating embeddings
            session: Database session
            redis: Redis service for caching
            metrics_service: Optional metrics tracking
            classifier: Optional query classifier for smart routing
        """
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.session = session
        self.redis = redis
        self.metrics_service = metrics_service
        self.classifier = classifier

    async def _retrieve_chunks(
        self,
        query: str,
        document_id: int | None = None,
        max_chunks: int = 5,
        min_score: float = 0.6,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks using semantic search with optimizations.

        Args:
            query: User's question
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

        # 🔧 OPTIMIZATION 1: Try to get cached embedding
        query_embedding = None

        if self.redis and self.redis.is_available:
            query_embedding = await self.redis.get_query_embedding(query)

            if query_embedding:
                # Cache hit - saved embedding computation
                if self.metrics_service:
                    await self.metrics_service.track_cache_hit("embedding")
            else:
                # Cache miss
                if self.metrics_service:
                    await self.metrics_service.track_cache_miss("embedding")

        if query_embedding is None:
            # Generate embedding (offload CPU-bound task to thread)
            query_embedding = await asyncio.to_thread(self.embedding_service.embed_text, query)

            # Cache for future use
            if self.redis and self.redis.is_available:
                await self.redis.set_query_embedding(query, query_embedding)

        # 🔧 OPTIMIZATION 2: Track search latency
        search_start = time.time()

        # Search Qdrant
        search_results = await self.vector_store.search(
            query_embedding=query_embedding,
            document_id=document_id,
            limit=max_chunks,
            score_threshold=min_score,
        )

        search_duration = (time.time() - search_start) * 1000
        if self.metrics_service:
            await self.metrics_service.track_search_latency(search_duration)

        logger.info(
            f"🔍 Vector search returned {len(search_results)} results "
            f"(took {search_duration:.0f}ms)"
        )

        # 🔧 OPTIMIZATION 3: Filter low-relevance chunks
        # Only include chunks above min_score threshold
        filtered_results = [
            result for result in search_results if result.get("score", 0) >= min_score
        ]

        if len(filtered_results) < len(search_results):
            logger.info(
                f"📊 Filtered out {len(search_results) - len(filtered_results)} "
                f"low-relevance chunks (score < {min_score})"
            )

        # Use data from Qdrant payload directly
        chunks_with_metadata = []
        for result in filtered_results:
            chunks_with_metadata.append(
                {
                    "chunk_id": result.get("chunk_id"),
                    "chunk_text": result.get("chunk_text", ""),
                    "chunk_position": result.get("chunk_index", 0),
                    "document_id": result.get("document_id"),
                    "document_title": result.get("metadata", {}).get("document_title", "Unknown"),
                    "similarity_score": result.get("score", 0.0),
                }
            )

        return chunks_with_metadata

    def _build_context(self, chunks: list[dict[str, Any]]) -> str:
        """Build context string from retrieved chunks."""
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
        """Build user prompt with context."""
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
        Answer a question using RAG with production optimizations.

        Args:
            query: User's question
            document_id: Optional specific document
            max_chunks: Maximum chunks to use
            min_score: Minimum similarity score

        Returns:
            Tuple of (answer, citations, provider, model, tokens_used)
        """
        # 🔧 OPTIMIZATION 4: Try cache first
        if self.redis and self.redis.is_available:
            cached_response = await self.redis.get_rag_response(
                query, document_id, max_chunks, min_score
            )

            if cached_response:
                # Cache hit - return cached response
                if self.metrics_service:
                    await self.metrics_service.track_cache_hit("rag_response")

                logger.info(f"✅ Returning cached response for: {query[:50]}...")
                return (
                    cached_response["answer"],
                    [Citation(**c) for c in cached_response["citations"]],
                    cached_response["provider"],
                    cached_response["model"],
                    cached_response.get("tokens_used"),
                )

            # Cache miss
            if self.metrics_service:
                await self.metrics_service.track_cache_miss("rag_response")

        # 🔧 OPTIMIZATION 5: Classify query complexity
        if self.classifier and self.metrics_service:
            complexity = self.classifier.classify(query)
            await self.metrics_service.track_query_complexity(complexity)

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
        llm_start = time.time()

        answer, provider, model, tokens = await self.llm_service.generate(
            system_prompt=settings.RAG_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        llm_duration = (time.time() - llm_start) * 1000

        # 🔧 OPTIMIZATION 6: Track metrics
        if self.metrics_service:
            await self.metrics_service.track_llm_latency(llm_duration, provider)
            if tokens:
                await self.metrics_service.track_tokens_used(tokens, provider)

        # Step 4: Build citations
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

        # 🔧 OPTIMIZATION 7: Cache response
        if self.redis and self.redis.is_available:
            cache_data = {
                "answer": answer,
                "citations": [c.model_dump() for c in citations],
                "provider": provider,
                "model": model,
                "tokens_used": tokens,
            }
            await self.redis.set_rag_response(query, document_id, max_chunks, min_score, cache_data)

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

        NOTE: Streaming responses bypass cache (can't cache incomplete streams).
        """
        # Track query complexity
        if self.classifier and self.metrics_service:
            complexity = self.classifier.classify(query)
            await self.metrics_service.track_query_complexity(complexity)

        # Step 1: Retrieve relevant chunks
        chunks = await self._retrieve_chunks(
            query=query,
            document_id=document_id,
            max_chunks=max_chunks,
            min_score=min_score,
        )

        if not chunks:
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

        yield {
            "type": "citations",
            "data": [citation.model_dump() for citation in citations],
        }

        # Step 3: Build context and prompt
        context = self._build_context(chunks)
        user_prompt = self._build_prompt(query, context)

        # Step 4: Stream the answer
        llm_start = time.time()
        total_tokens = None
        provider = "none"

        async for event in self.llm_service.generate_stream(
            system_prompt=settings.RAG_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        ):
            if event.get("type") == "usage":
                total_tokens = event.get("data", {}).get("total_tokens")
            provider = event.get("provider", "none")
            yield event

        # Track metrics
        llm_duration = (time.time() - llm_start) * 1000
        if self.metrics_service:
            await self.metrics_service.track_llm_latency(llm_duration, provider)
            if total_tokens:
                await self.metrics_service.track_tokens_used(total_tokens, provider)
