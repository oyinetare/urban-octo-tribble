"""Query routes for RAG-based Q&A."""

import logging
import time

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.core import get_session
from app.dependencies import (
    get_current_user,
    get_embedding_service,
    get_rag_service,
    get_vector_service,
    pagination_params,
    verify_document_ownership,
)
from app.models import Document, Query, User
from app.schemas import PaginatedResponse, PaginationParams
from app.schemas.query import QueryHistoryResponse, QueryRequest, QueryResponse
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.embeddings import EmbeddingService
from app.services.rag import RAGService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sematic", response_model=SearchResponse)
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


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question across all documents",
    description="Ask a question and get an AI-generated answer based on your documents",
    tags=["Documents"],
)
async def query_documents(
    request: QueryRequest,
    current_user: User = Security(get_current_user, scopes=["read"]),
    rag_service: RAGService = Depends(get_rag_service),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    """
    Ask a question across all user's documents.

    This endpoint:
    1. Searches for relevant chunks across all user's documents
    2. Builds context from top matching chunks
    3. Generates an answer using LLM
    4. Returns answer with citations
    """
    start_time = time.time()

    # Generate answer
    answer, citations, provider, model, tokens = await rag_service.ask(
        query=request.query,
        # user_id=current_user.id,
        document_id=request.document_id,
        max_chunks=request.max_chunks,
        min_score=request.min_score,
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    # Save query to database
    query_record = Query(
        user_id=current_user.id,
        document_id=request.document_id,
        query=request.query,
        answer=answer,
        chunks_used=[c.chunk_id for c in citations],
        llm_provider=provider,
        llm_model=model,
        tokens_used=tokens,
        response_time_ms=response_time_ms,
    )
    session.add(query_record)
    await session.commit()

    return QueryResponse(
        query=request.query,
        answer=answer,
        citations=citations,
        llm_provider=provider,
        llm_model=model,
        tokens_used=tokens,
        response_time_ms=response_time_ms,
    )


@router.post(
    "/{document_id}/ask",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about a specific document",
    description="Ask a question about a specific document and get an AI-generated answer",
    tags=["Documents"],
)
async def query_document(
    request: QueryRequest,
    document: Document = Depends(verify_document_ownership),
    current_user: User = Security(get_current_user, scopes=["read"]),
    rag_service: RAGService = Depends(get_rag_service),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    """
    Ask a question about a specific document.

    This endpoint:
    1. Searches for relevant chunks in the specified document only
    2. Builds context from top matching chunks
    3. Generates an answer using LLM
    4. Returns answer with citations
    """
    start_time = time.time()

    # Override document_id from request with verified document
    answer, citations, provider, model, tokens = await rag_service.ask(
        query=request.query,
        # user_id=current_user.id,
        document_id=document.id,
        max_chunks=request.max_chunks,
        min_score=request.min_score,
    )

    response_time_ms = int((time.time() - start_time) * 1000)

    # Save query to database
    query_record = Query(
        user_id=current_user.id,
        document_id=document.id,
        query=request.query,
        answer=answer,
        chunks_used=[c.chunk_id for c in citations],
        llm_provider=provider,
        llm_model=model,
        tokens_used=tokens,
        response_time_ms=response_time_ms,
    )
    session.add(query_record)
    await session.commit()

    return QueryResponse(
        query=request.query,
        answer=answer,
        citations=citations,
        llm_provider=provider,
        llm_model=model,
        tokens_used=tokens,
        response_time_ms=response_time_ms,
    )


@router.get(
    "/history",
    response_model=PaginatedResponse[QueryHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get query history",
    description="Get paginated list of user's query history",
)
async def get_query_history(
    current_user: User = Security(get_current_user, scopes=["read"]),
    pagination: PaginationParams = Depends(pagination_params),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[QueryHistoryResponse]:
    """Get user's query history with pagination."""
    # Count total queries
    count_stmt = select(Query).where(Query.user_id == current_user.id)
    count_result = await session.execute(count_stmt)
    total = len(count_result.all())

    # Get paginated queries
    offset = (pagination.page - 1) * pagination.page_size
    stmt = (
        select(Query)
        .where(Query.user_id == current_user.id)
        .order_by(desc(Query.created_at))
        .offset(offset)
        .limit(pagination.page_size)
    )
    result = await session.execute(stmt)
    queries = result.scalars().all()

    return PaginatedResponse(
        items=[QueryHistoryResponse.model_validate(q) for q in queries],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get(
    "/{query_id}",
    response_model=QueryHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get specific query",
    description="Get details of a specific query",
)
async def get_query(
    query_id: int,
    current_user: User = Security(get_current_user, scopes=["read"]),
    session: AsyncSession = Depends(get_session),
) -> QueryHistoryResponse:
    """Get a specific query by ID."""
    stmt = select(Query).where(Query.id == query_id, Query.user_id == current_user.id)
    result = await session.execute(stmt)
    query = result.scalar_one_or_none()

    if not query:
        from app.exceptions import AppException

        raise AppException(
            message="Query not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return QueryHistoryResponse.model_validate(query)
