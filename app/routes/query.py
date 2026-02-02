"""Query routes for RAG-based Q&A."""

import json
import logging
import time

from fastapi import APIRouter, Depends, Security, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.core import get_session
from app.dependencies import (
    get_current_user,
    get_embedding_service,
    get_hybrid_search_service,
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
from app.services.hybrid_search import HybridSearchService
from app.services.rag import RAGService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/semantic", response_model=SearchResponse, deprecated=True)
async def semantic_search(
    search_request: SearchRequest,
    current_user: User = Security(get_current_user, scopes=["read"]),
    session: AsyncSession = Depends(get_session),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_service),
) -> SearchResponse:
    """
    Legacy endpoint for semantic search only.

    **Deprecated**: Use `/search` with `mode="vector"` instead.

    This endpoint performs vector-only semantic search without full-text search.

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
        # Generate embedding for the search query
        logger.info(f"Generating embedding for query: {search_request.query[:50]}...")
        query_embedding = embedding_service.embed_text(search_request.query)

        # Search the vector store
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

        # Format results
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
            mode="vector",
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
        chunks_used=[c.chunk_id for c in citations if c.chunk_id is not None],  # Filter None values
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
    # tags=["Documents"],
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
        document_id=request.document_id,
        query=request.query,
        answer=answer,
        chunks_used=[c.chunk_id for c in citations if c.chunk_id is not None],  # Filter None values
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
    "/{query_id}/ask/stream",
    summary="Stream answer for a specific query",
    description="Get a streaming answer by re-running a previous query",
)
async def stream_query_by_id(
    query_id: int,
    current_user: User = Security(get_current_user, scopes=["read"]),
    rag_service: RAGService = Depends(get_rag_service),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Re-run a previous query and stream the response.

    This endpoint:
    1. Fetches the original query from history
    2. Re-runs the RAG pipeline
    3. Streams the answer token-by-token using Server-Sent Events

    **SSE Event Format:**
    ```
    event: citations
    data: [{"chunk_id": 1, "document_id": 2, ...}]

    event: token
    data: {"text": "Hello", "provider": "anthropic", "model": "claude-3-sonnet"}

    event: usage
    data: {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}

    event: done
    data: {"query_id": 123, "full_answer": "Complete answer text"}
    ```
    """
    # Fetch the original query
    stmt = select(Query).where(Query.id == query_id, Query.user_id == current_user.id)
    result = await session.execute(stmt)
    original_query = result.scalar_one_or_none()

    if not original_query:
        from app.exceptions import AppException

        raise AppException(
            message="Query not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    async def event_generator():
        """Generate SSE events for streaming response."""
        start_time = time.time()
        full_answer = ""
        provider = "none"
        model = "none"
        tokens_used = None
        chunks_used = []

        try:
            # Stream the RAG response
            async for event in rag_service.ask_stream(
                query=original_query.query,
                document_id=original_query.document_id,
                max_chunks=5,  # Use same defaults as original
                min_score=0.6,
            ):
                event_type = event.get("type")

                if event_type == "citations":
                    # Send citations as first event
                    citations_data = event.get("data", [])
                    chunks_used = [c.get("chunk_id") for c in citations_data if c.get("chunk_id")]
                    yield f"event: citations\ndata: {json.dumps(citations_data)}\n\n"

                elif event_type == "token":
                    # Stream text tokens
                    token = event.get("data", "")
                    full_answer += token
                    provider = event.get("provider", "none")
                    model = event.get("model", "none")

                    token_data = {
                        "text": token,
                        "provider": provider,
                        "model": model,
                    }
                    yield f"event: token\ndata: {json.dumps(token_data)}\n\n"

                elif event_type == "usage":
                    # Send token usage stats
                    usage_data = event.get("data", {})
                    tokens_used = usage_data.get("total_tokens")
                    yield f"event: usage\ndata: {json.dumps(usage_data)}\n\n"

                elif event_type == "error":
                    # Send error event
                    error_data = {"error": event.get("data", "Unknown error")}
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    return

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Save the new query to database
            query_record = Query(
                user_id=current_user.id,
                document_id=original_query.document_id,
                query=original_query.query,
                answer=full_answer,
                chunks_used=chunks_used,
                llm_provider=provider,
                llm_model=model,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
            )
            session.add(query_record)
            await session.commit()
            await session.refresh(query_record)

            # Send completion event with full answer and new query ID
            done_data = {
                "query_id": query_record.id,
                "full_answer": full_answer,
                "response_time_ms": response_time_ms,
            }
            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post(
    "/stream",
    summary="Ask a question with streaming response",
    description="Ask a question and get a streaming AI-generated answer",
)
async def query_documents_stream(
    request: QueryRequest,
    current_user: User = Security(get_current_user, scopes=["read"]),
    rag_service: RAGService = Depends(get_rag_service),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Ask a question across all user's documents with streaming response.

    This endpoint:
    1. Searches for relevant chunks across all user's documents
    2. Builds context from top matching chunks
    3. Streams the answer token-by-token using Server-Sent Events
    4. Saves the complete query to history when done

    **SSE Event Types:**
    - `citations`: Initial citations before streaming starts
    - `token`: Individual text tokens as they're generated
    - `usage`: Token usage statistics (sent at the end)
    - `done`: Completion event with full answer and query ID
    - `error`: Error information if something goes wrong
    """

    async def event_generator():
        """Generate SSE events for streaming response."""
        start_time = time.time()
        full_answer = ""
        provider = "none"
        model = "none"
        tokens_used = None
        chunks_used = []

        try:
            # Stream the RAG response
            async for event in rag_service.ask_stream(
                query=request.query,
                document_id=request.document_id,
                max_chunks=request.max_chunks,
                min_score=request.min_score,
            ):
                event_type = event.get("type")

                if event_type == "citations":
                    # Send citations as first event
                    citations_data = event.get("data", [])
                    chunks_used = [c.get("chunk_id") for c in citations_data if c.get("chunk_id")]
                    yield f"event: citations\ndata: {json.dumps(citations_data)}\n\n"

                elif event_type == "token":
                    # Stream text tokens
                    token = event.get("data", "")
                    full_answer += token
                    provider = event.get("provider", "none")
                    model = event.get("model", "none")

                    token_data = {
                        "text": token,
                        "provider": provider,
                        "model": model,
                    }
                    yield f"event: token\ndata: {json.dumps(token_data)}\n\n"

                elif event_type == "usage":
                    # Send token usage stats
                    usage_data = event.get("data", {})
                    tokens_used = usage_data.get("total_tokens")
                    yield f"event: usage\ndata: {json.dumps(usage_data)}\n\n"

                elif event_type == "error":
                    # Send error event
                    error_data = {"error": event.get("data", "Unknown error")}
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    return

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Save query to database
            query_record = Query(
                user_id=current_user.id,
                document_id=request.document_id,
                query=request.query,
                answer=full_answer,
                chunks_used=chunks_used,
                llm_provider=provider,
                llm_model=model,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
            )
            session.add(query_record)
            await session.commit()
            await session.refresh(query_record)

            # Send completion event with full answer and query ID
            done_data = {
                "query_id": query_record.id,
                "full_answer": full_answer,
                "response_time_ms": response_time_ms,
            }
            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post(
    "/{document_id}/ask/stream",
    summary="Ask about a specific document with streaming",
    description="Ask a question about a specific document with streaming response",
    # tags=["Documents"],
)
async def query_document_stream(
    request: QueryRequest,
    document: Document = Depends(verify_document_ownership),
    current_user: User = Security(get_current_user, scopes=["read"]),
    rag_service: RAGService = Depends(get_rag_service),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Ask a question about a specific document with streaming response.

    This endpoint:
    1. Searches for relevant chunks in the specified document only
    2. Builds context from top matching chunks
    3. Streams the answer token-by-token using Server-Sent Events
    4. Saves the complete query to history when done
    """

    async def event_generator():
        """Generate SSE events for streaming response."""
        start_time = time.time()
        full_answer = ""
        provider = "none"
        model = "none"
        tokens_used = None
        chunks_used = []

        try:
            # Stream the RAG response (use verified document.id)
            async for event in rag_service.ask_stream(
                query=request.query,
                document_id=document.id,  # Use verified document
                max_chunks=request.max_chunks,
                min_score=request.min_score,
            ):
                event_type = event.get("type")

                if event_type == "citations":
                    # Send citations as first event
                    citations_data = event.get("data", [])
                    chunks_used = [c.get("chunk_id") for c in citations_data if c.get("chunk_id")]
                    yield f"event: citations\ndata: {json.dumps(citations_data)}\n\n"

                elif event_type == "token":
                    # Stream text tokens
                    token = event.get("data", "")
                    full_answer += token
                    provider = event.get("provider", "none")
                    model = event.get("model", "none")

                    token_data = {
                        "text": token,
                        "provider": provider,
                        "model": model,
                    }
                    yield f"event: token\ndata: {json.dumps(token_data)}\n\n"

                elif event_type == "usage":
                    # Send token usage stats
                    usage_data = event.get("data", {})
                    tokens_used = usage_data.get("total_tokens")
                    yield f"event: usage\ndata: {json.dumps(usage_data)}\n\n"

                elif event_type == "error":
                    # Send error event
                    error_data = {"error": event.get("data", "Unknown error")}
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    return

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Save query to database
            query_record = Query(
                user_id=current_user.id,
                document_id=document.id,  # Use verified document
                query=request.query,
                answer=full_answer,
                chunks_used=chunks_used,
                llm_provider=provider,
                llm_model=model,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
            )
            session.add(query_record)
            await session.commit()
            await session.refresh(query_record)

            # Send completion event
            done_data = {
                "query_id": query_record.id,
                "full_answer": full_answer,
                "response_time_ms": response_time_ms,
            }
            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
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


@router.post("/search", response_model=SearchResponse)
async def hybrid_search(
    search_request: SearchRequest,
    current_user: User = Security(get_current_user, scopes=["read"]),
    hybrid_search_service: HybridSearchService = Depends(get_hybrid_search_service),
) -> SearchResponse:
    """
    Perform hybrid search combining vector similarity and full-text search.

    This endpoint uses Reciprocal Rank Fusion (RRF) to merge results from:
    - **Vector search**: Semantic similarity using embeddings
    - **Keyword search**: Full-text search using PostgreSQL

    **Search Modes:**
    - `hybrid` (default): Combines vector + keyword search with RRF
    - `vector`: Semantic search only (good for conceptual queries)
    - `keyword`: Full-text search only (good for exact phrases)

    **Parameters:**
    - **query**: The text you want to search for (1-1000 characters)
    - **document_id**: (Optional) Limit search to a specific document
    - **limit**: Maximum number of results to return (1-50, default: 5)
    - **score_threshold**: Minimum similarity score 0-1 (default: 0.7)
    - **mode**: Search mode - 'hybrid', 'vector', or 'keyword' (default: 'hybrid')

    **Returns:**
    - List of matching chunks ranked by relevance
    - Each result includes scores from both search methods (in hybrid mode)
    - Chunks are deduplicated and re-ranked using RRF

    **Example Request:**
    ```json
    {
        "query": "climate change impacts on agriculture",
        "mode": "hybrid",
        "limit": 10,
        "score_threshold": 0.6
    }
    ```

    **Example Response:**
    ```json
    {
        "query": "climate change impacts",
        "mode": "hybrid",
        "results": [
            {
                "chunk_text": "Climate change significantly affects crop yields...",
                "document_id": 123,
                "chunk_index": 5,
                "score": 0.89,
                "vector_score": 0.85,
                "keyword_score": 0.92,
                "rrf_score": 0.0327,
                "metadata": {"document_title": "Agriculture Report 2024"}
            }
        ],
        "total_results": 1
    }
    ```

    **Why Hybrid Search?**
    - **Vector search** captures semantic meaning: "car" matches "automobile"
    - **Keyword search** ensures exact matches: "Model X" finds exact phrase
    - **RRF** combines both for best accuracy

    **When to use each mode:**
    - `hybrid`: Best default choice, combines strengths of both methods
    - `vector`: Conceptual queries, finding similar ideas
    - `keyword`: Exact phrases, technical terms, proper nouns
    """
    try:
        # Perform hybrid search
        logger.info(
            f"Hybrid search: query='{search_request.query[:50]}...', "
            f"mode={search_request.mode}, limit={search_request.limit}"
        )

        results = await hybrid_search_service.hybrid_search(
            query=search_request.query,
            document_id=search_request.document_id,
            limit=search_request.limit,
            score_threshold=search_request.score_threshold,
            mode=search_request.mode,
        )

        # Format results
        search_results = [
            SearchResult(
                chunk_text=result["chunk_text"],
                document_id=result["document_id"],
                chunk_index=result["chunk_index"],
                score=result.get("rrf_score") or result.get("score", 0.0),
                metadata=result.get("metadata", {}),
                vector_score=result.get("vector_score"),
                keyword_score=result.get("keyword_score"),
                rrf_score=result.get("rrf_score"),
            )
            for result in results
        ]

        logger.info(
            f"Search completed. Found {len(search_results)} results using {search_request.mode} mode."
        )

        return SearchResponse(
            query=search_request.query,
            results=search_results,
            total_results=len(search_results),
            mode=search_request.mode,
        )

    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        raise
