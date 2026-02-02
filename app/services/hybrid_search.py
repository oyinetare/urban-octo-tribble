"""
Hybrid Search Service

Combines vector (semantic) search with PostgreSQL full-text search (keyword)
using Reciprocal Rank Fusion (RRF) for optimal results.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select, text

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
settings = get_settings()


class HybridSearchService:
    """
    Hybrid search combining vector similarity and full-text search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both methods,
    providing better accuracy than either method alone.
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        session: AsyncSession,
    ):
        """
        Initialize hybrid search service.

        Args:
            vector_store: Vector store for semantic search
            embedding_service: Service for generating embeddings
            session: Database session for full-text search
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.session = session
        self.rrf_k = 60  # Standard RRF parameter

    async def vector_search(
        self,
        query: str,
        document_id: int | None = None,
        limit: int = 20,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Perform vector (semantic) search.

        Args:
            query: Search query text
            document_id: Optional document ID filter
            limit: Maximum results (default 20 for fusion)
            score_threshold: Minimum similarity score

        Returns:
            List of results with chunk_id, score, and rank
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Search vector store
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            document_id=document_id,
            limit=limit,
            score_threshold=score_threshold,
        )

        # Format results with rank
        ranked_results = []
        for rank, result in enumerate(results, start=1):
            ranked_results.append(
                {
                    "chunk_id": result["chunk_id"],
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"],
                    "chunk_text": result["chunk_text"],
                    "score": result["score"],
                    "rank": rank,
                    "metadata": result.get("metadata", {}),
                }
            )

        logger.info(f"Vector search returned {len(ranked_results)} results")
        return ranked_results

    async def keyword_search(
        self,
        query: str,
        document_id: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Perform PostgreSQL full-text search.

        Args:
            query: Search query text
            document_id: Optional document ID filter
            limit: Maximum results (default 20 for fusion)

        Returns:
            List of results with chunk_id, score, and rank
        """
        # Build the full-text search query
        # ts_rank returns relevance score (higher is better)

        # Initialize select with col() to expose SQLAlchemy attributes
        stmt = select(
            col(Chunk.id).label("chunk_id"),
            col(Chunk.document_id),  # Optional col() here for consistency
            col(Chunk.position).label("chunk_index"),
        )

        # Add columns, wrapping text_vector so ts_rank works
        tsquery = func.plainto_tsquery("english", query)
        stmt = stmt.add_columns(
            col(Chunk.text).label("chunk_text"),
            func.ts_rank(col(Chunk.text_vector), tsquery).label("score"),
        )

        # Use col() for the full-text match operator
        stmt = stmt.where(col(Chunk.text_vector).op("@@")(tsquery))

        # Use col() for the ID comparison to return an expression, not a bool
        if document_id is not None:
            stmt = stmt.where(col(Chunk.document_id) == document_id)

        # Order by the string label "score" and apply limit
        stmt = stmt.order_by(text("score DESC")).limit(limit)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Format results with rank
        ranked_results = []
        for rank, row in enumerate(rows, start=1):
            ranked_results.append(
                {
                    "chunk_id": row.chunk_id,
                    "document_id": row.document_id,
                    "chunk_index": row.chunk_index,
                    "chunk_text": row.chunk_text,
                    "score": float(row.score),
                    "rank": rank,
                    "metadata": {},
                }
            )

        logger.info(f"Keyword search returned {len(ranked_results)} results")
        return ranked_results

    def reciprocal_rank_fusion(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).

        RRF Formula: score(d) = Σ 1 / (k + rank(d))

        Where:
        - d = document (chunk)
        - k = constant (typically 60)
        - rank(d) = rank of document in that result set

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            k: RRF constant (default 60)

        Returns:
            Merged and re-ranked results
        """
        # Build a map of chunk_id -> RRF score
        rrf_scores: dict[int, float] = {}
        chunk_data: dict[int, dict[str, Any]] = {}

        # Process vector results
        for result in vector_results:
            chunk_id = result["chunk_id"]
            if chunk_id is None:
                continue

            rank = result["rank"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

            # Store chunk data (prefer vector result for metadata)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"],
                    "chunk_text": result["chunk_text"],
                    "metadata": result.get("metadata", {}),
                    "vector_score": result["score"],
                    "keyword_score": None,
                }

        # Process keyword results
        for result in keyword_results:
            chunk_id = result["chunk_id"]
            if chunk_id is None:
                continue

            rank = result["rank"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

            # Update or create chunk data
            if chunk_id in chunk_data:
                chunk_data[chunk_id]["keyword_score"] = result["score"]
            else:
                chunk_data[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"],
                    "chunk_text": result["chunk_text"],
                    "metadata": result.get("metadata", {}),
                    "vector_score": None,
                    "keyword_score": result["score"],
                }

        # Combine and sort by RRF score
        merged_results = []
        for chunk_id, rrf_score in rrf_scores.items():
            data = chunk_data[chunk_id]
            data["rrf_score"] = rrf_score
            merged_results.append(data)

        # Sort by RRF score (descending)
        merged_results.sort(key=lambda x: x["rrf_score"], reverse=True)

        logger.info(
            f"RRF merged {len(vector_results)} vector + {len(keyword_results)} keyword "
            f"→ {len(merged_results)} unique results"
        )

        return merged_results

    async def hybrid_search(
        self,
        query: str,
        document_id: int | None = None,
        limit: int = 5,
        score_threshold: float = 0.0,
        mode: str = "hybrid",
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query text
            document_id: Optional document ID filter
            limit: Final number of results to return
            score_threshold: Minimum similarity score for vector search
            mode: Search mode - 'hybrid' (default), 'vector', or 'keyword'

        Returns:
            Ranked search results with scores
        """
        if mode == "vector":
            # Vector-only search
            results = await self.vector_search(
                query=query,
                document_id=document_id,
                limit=limit,
                score_threshold=score_threshold,
            )
            return results[:limit]

        elif mode == "keyword":
            # Keyword-only search
            results = await self.keyword_search(
                query=query,
                document_id=document_id,
                limit=limit,
            )
            return results[:limit]

        else:  # mode == "hybrid"
            # Get more results from each method for better fusion
            fetch_limit = limit * 4  # Fetch 4x for fusion

            # Run both searches in parallel
            import asyncio

            vector_results, keyword_results = await asyncio.gather(
                self.vector_search(
                    query=query,
                    document_id=document_id,
                    limit=fetch_limit,
                    score_threshold=score_threshold,
                ),
                self.keyword_search(
                    query=query,
                    document_id=document_id,
                    limit=fetch_limit,
                ),
            )

            # Merge using RRF
            merged_results = self.reciprocal_rank_fusion(
                vector_results=vector_results,
                keyword_results=keyword_results,
                k=self.rrf_k,
            )

            # Return top results
            return merged_results[:limit]
