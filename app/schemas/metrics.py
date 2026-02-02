"""
Schemas for metrics endpoints.

Add this to app/schemas/metrics.py
"""

from typing import Any

from pydantic import BaseModel, Field


class CacheMetrics(BaseModel):
    """Cache statistics."""

    enabled: bool = Field(description="Whether caching is enabled")
    rag_responses_cached: int = Field(
        default=0,
        description="Number of cached RAG responses",
    )
    embeddings_cached: int = Field(
        default=0,
        description="Number of cached embeddings",
    )
    response_ttl_seconds: int = Field(
        default=3600,
        description="TTL for RAG response cache",
    )
    embedding_ttl_seconds: int = Field(
        default=86400,
        description="TTL for embedding cache",
    )
    message: str | None = Field(
        default=None,
        description="Status message if cache is disabled",
    )


class LatencyMetrics(BaseModel):
    """Latency statistics."""

    search_avg_ms: float = Field(
        default=0.0,
        description="Average search latency in milliseconds",
    )
    search_p95_ms: float = Field(
        default=0.0,
        description="95th percentile search latency",
    )
    llm_anthropic_avg_ms: float = Field(
        default=0.0,
        description="Average Anthropic LLM latency",
    )
    llm_ollama_avg_ms: float = Field(
        default=0.0,
        description="Average Ollama LLM latency",
    )


class QueryComplexityDistribution(BaseModel):
    """Query complexity distribution percentages."""

    simple_pct: float = Field(description="Percentage of simple queries")
    moderate_pct: float = Field(description="Percentage of moderate queries")
    complex_pct: float = Field(description="Percentage of complex queries")


class QueryComplexityMetrics(BaseModel):
    """Query complexity statistics."""

    total: int = Field(description="Total number of queries")
    simple: int = Field(description="Number of simple queries")
    moderate: int = Field(description="Number of moderate queries")
    complex: int = Field(description="Number of complex queries")
    distribution: QueryComplexityDistribution


class TokenUsageMetrics(BaseModel):
    """Token usage statistics."""

    anthropic: int = Field(description="Tokens used by Anthropic")
    ollama: int = Field(description="Tokens used by Ollama")
    total: int = Field(description="Total tokens used")


class CacheHitRates(BaseModel):
    """Cache hit rate statistics."""

    rag_response_hit_rate: str = Field(description="RAG response cache hit rate")
    embedding_hit_rate: str = Field(description="Embedding cache hit rate")


class PerformanceMetrics(BaseModel):
    """Complete performance metrics."""

    enabled: bool = Field(description="Whether metrics tracking is enabled")
    cache: CacheHitRates | None = None
    latency: LatencyMetrics | None = None
    query_complexity: QueryComplexityMetrics | None = None
    tokens: TokenUsageMetrics | None = None
    message: str | None = Field(
        default=None,
        description="Status message if metrics are disabled",
    )


class MetricsSummaryResponse(BaseModel):
    """Complete metrics summary response."""

    cache: dict[str, Any] = Field(description="Cache statistics")
    performance: dict[str, Any] = Field(description="Performance metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "cache": {
                    "enabled": True,
                    "rag_responses_cached": 150,
                    "embeddings_cached": 320,
                    "response_ttl_seconds": 3600,
                    "embedding_ttl_seconds": 86400,
                },
                "performance": {
                    "enabled": True,
                    "cache": {
                        "rag_response_hit_rate": "45.2%",
                        "embedding_hit_rate": "67.8%",
                    },
                    "latency": {
                        "search_avg_ms": 85.3,
                        "search_p95_ms": 142.7,
                        "llm_anthropic_avg_ms": 1234.5,
                        "llm_ollama_avg_ms": 987.2,
                    },
                    "query_complexity": {
                        "total": 1000,
                        "simple": 450,
                        "moderate": 380,
                        "complex": 170,
                        "distribution": {
                            "simple_pct": 45.0,
                            "moderate_pct": 38.0,
                            "complex_pct": 17.0,
                        },
                    },
                    "tokens": {
                        "anthropic": 125000,
                        "ollama": 0,
                        "total": 125000,
                    },
                },
            }
        }
