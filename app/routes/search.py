import logging

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_session
from app.dependencies import get_current_user, get_embedding_service, get_vector_service
from app.models import User
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services import EmbeddingService, VectorStoreService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    current_user: User = Security(get_current_user, scopes=["read"]),
    session: AsyncSession = Depends(get_session),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_service),
) -> SearchResponse:
    """
    Perform semantic search across documents using vector embeddings.

    This endpoint converts your search query into an embedding vector and finds
    the most semantically similar chunks across your documents.

    **Parameters:**
    - **query**: The text you want to search for (1-1000 characters)
    - **document_id**: (Optional) Limit search to a specific document
    - **limit**: Maximum number of results to return (1-50, default: 5)
    - **score_threshold**: Minimum similarity score 0-1 (default: 0.7)

    **Returns:**
    - List of matching chunks with similarity scores
    - Chunks are ranked by relevance (highest score first)
    - Each result includes the chunk text, document info, and metadata

    **Example Request:**
    ```json
    {
        "query": "What are the main findings about climate change?",
        "limit": 5,
        "score_threshold": 0.7
    }
    ```

    **Example Response:**
    ```json
    {
        "query": "climate change findings",
        "results": [
            {
                "chunk_text": "Climate change is causing significant impacts...",
                "document_id": 123,
                "chunk_index": 5,
                "score": 0.89,
                "metadata": {
                    "document_title": "Climate Report 2024",
                    "user_id": 1
                }
            }
        ],
        "total_results": 1
    }
    ```

    **Performance:**
    - Search typically completes in < 100ms for collections with millions of vectors
    - Uses HNSW index for fast approximate nearest neighbor search
    - Automatically batches embedding generation for efficiency
    """
    try:
        # Step 1: Generate embedding for the search query
        logger.info(f"Generating embedding for query: {search_request.query[:50]}...")
        query_embedding = embedding_service.embed_text(search_request.query)

        # Step 2: Search the vector store
        logger.info(
            f"Searching vector store with limit={search_request.limit}, "
            f"threshold={search_request.score_threshold}, "
            f"document_id={search_request.document_id}"
        )

        raw_results = await vector_store.search(
            query_embedding=query_embedding,
            document_id=search_request.document_id,
            limit=search_request.limit,
            score_threshold=search_request.score_threshold,
        )

        # Step 3: Format results
        search_results = [
            SearchResult(
                chunk_text=result["chunk_text"],
                document_id=result["document_id"],
                chunk_index=result["chunk_index"],
                score=result["score"],
                metadata=result["metadata"],
            )
            for result in raw_results
        ]

        logger.info(f"Search completed. Found {len(search_results)} results.")

        return SearchResponse(
            query=search_request.query,
            results=search_results,
            total_results=len(search_results),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise
