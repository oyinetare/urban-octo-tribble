"""
Metrics and monitoring endpoints for production optimization.

Endpoints:
- GET /metrics/cache - Cache statistics
- GET /metrics/performance - Performance metrics
- GET /metrics/summary - Complete metrics summary
- DELETE /cache/documents/{document_id} - Invalidate cache
"""

import logging

from fastapi import APIRouter, Depends, Security, status
from fastapi.responses import JSONResponse

from app.core import services
from app.dependencies import get_current_user, verify_document_ownership
from app.models import Document, User
from app.schemas import MetricsSummaryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/cache",
    summary="Get cache statistics",
    description="View cache hit rates and cached entry counts",
)
async def get_cache_stats(
    current_user: User = Security(get_current_user, scopes=["read"]),
):
    """
    Get cache statistics.

    Shows:
    - Number of cached RAG responses
    - Number of cached embeddings
    - Cache TTL settings
    - Whether caching is enabled

    Example Response:
    ```json
    {
        "enabled": true,
        "rag_responses_cached": 150,
        "embeddings_cached": 320,
        "response_ttl_seconds": 3600,
        "embedding_ttl_seconds": 86400
    }
    ```
    """
    if not services.redis or not services.redis.is_available:
        return {
            "enabled": False,
            "message": "Cache service not available (Redis required)",
        }

    stats = await services.redis.get_cache_stats()
    return stats


@router.get(
    "/performance",
    summary="Get performance metrics",
    description="View latency metrics and query complexity distribution",
)
async def get_performance_metrics(
    current_user: User = Security(get_current_user, scopes=["read"]),
):
    """
    Get performance metrics.

    Shows:
    - Cache hit rates (RAG responses and embeddings)
    - Latency metrics (search, LLM)
    - Query complexity distribution
    - Token usage by provider

    Example Response:
    ```json
    {
        "cache": {
            "rag_response_hit_rate": "45.2%",
            "embedding_hit_rate": "67.8%"
        },
        "latency": {
            "search_avg_ms": 85.3,
            "search_p95_ms": 142.7,
            "llm_anthropic_avg_ms": 1234.5,
            "llm_ollama_avg_ms": 987.2
        },
        "query_complexity": {
            "total": 1000,
            "simple": 450,
            "moderate": 380,
            "complex": 170,
            "distribution": {
                "simple_pct": 45.0,
                "moderate_pct": 38.0,
                "complex_pct": 17.0
            }
        },
        "tokens": {
            "anthropic": 125000,
            "ollama": 0,
            "total": 125000
        }
    }
    ```
    """
    if not services.metrics or not services.metrics.is_available:
        return {
            "enabled": False,
            "message": "Metrics service not available (Redis required)",
        }

    metrics = await services.metrics.get_metrics_summary()
    return metrics


@router.get(
    "/summary",
    response_model=MetricsSummaryResponse,
    summary="Get complete metrics summary",
    description="Comprehensive view of all performance metrics",
)
async def get_metrics_summary(
    current_user: User = Security(get_current_user, scopes=["read"]),
) -> MetricsSummaryResponse:
    """
    Get comprehensive metrics summary.

    Combines cache and performance metrics into a single response.
    Useful for dashboards and monitoring.
    """
    cache_stats = {}
    performance_stats = {}

    if services.redis and services.redis.is_available:
        cache_stats = await services.redis.get_cache_stats()

    if services.metrics and services.metrics.is_available:
        performance_stats = await services.metrics.get_metrics_summary()

    return MetricsSummaryResponse(
        cache=cache_stats,
        performance=performance_stats,
    )


@router.delete(
    "/cache/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate document cache",
    description="Clear all cached responses for a specific document",
)
async def invalidate_document_cache(
    document: Document = Depends(verify_document_ownership),
):
    """
    Invalidate all cached responses for a document.

    Call this endpoint when:
    - Document is updated
    - Document is re-processed
    - You want to force fresh responses

    Returns:
    - 204 No Content on success
    """
    if not services.redis or not services.redis.is_available:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "message": "Cache service not available",
            },
        )

    deleted = await services.redis.invalidate_document_cache(document.id)

    logger.info(f"Invalidated {deleted} cache entries for document {document.id}")

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )


@router.post(
    "/cache/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all cache (admin only)",
    description="Clear entire cache - use with caution",
)
async def clear_all_cache(
    current_user: User = Security(get_current_user, scopes=["admin"]),
):
    """
    Clear all cached data.

    **Admin only** - Clears:
    - All RAG responses
    - All embeddings
    - All metrics

    Use with caution - this will impact performance until cache is rebuilt.
    """
    if not services.redis or not services.redis.is_available:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "Redis not available"},
        )

    try:
        deleted = await services.redis.clear_all_cache()

        logger.warning(f"Admin {current_user.username} cleared entire cache ({deleted} keys)")

        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None,
        )

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Failed to clear cache: {str(e)}"},
        )
