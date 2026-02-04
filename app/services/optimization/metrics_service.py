"""
Performance metrics tracking for RAG optimization.

Tracks:
- Search latency
- LLM latency
- Cache hit rates
- Query complexity distribution
- Cost savings from caching
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from app.services.optimization.redis_service import RedisService

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Track performance metrics for RAG system.

    Metrics stored in Redis with sliding window (last 24 hours).
    All metrics are prefixed with 'metrics:' for easy identification.
    """

    def __init__(self, redis: RedisService | None):
        """
        Initialize metrics service.

        Args:
            redis: Redis service instance (optional)
        """
        self.redis = redis
        self.metrics_ttl = 86400  # 24 hours

    @property
    def is_available(self) -> bool:
        """Check if metrics tracking is available."""
        return self.redis is not None and self.redis.is_available

    async def _increment_counter(self, key: str, amount: int = 1) -> None:
        """Increment a counter metric."""
        if not self.is_available:
            return

        redis_client = self.redis.client  # type: ignore[union-attr]
        if not redis_client:
            return

        try:
            full_key = f"metrics:{key}"
            await redis_client.incr(full_key, amount)
            await redis_client.expire(full_key, self.metrics_ttl)
        except Exception as e:
            logger.error(f"Error incrementing counter {key}: {e}")

    async def _add_timing(self, key: str, duration_ms: float) -> None:
        """Add a timing metric (using sorted set for percentile calculation)."""
        if not self.is_available:
            return

        redis_client = self.redis.client  # type: ignore[union-attr]
        if not redis_client:
            return

        try:
            # Use sorted set with timestamp as score
            timestamp = time.time()
            full_key = f"metrics:timing:{key}"

            await redis_client.zadd(
                full_key,
                {f"{timestamp}:{duration_ms}": timestamp},
            )

            # Expire old entries (keep last 24 hours)
            cutoff = timestamp - self.metrics_ttl
            await redis_client.zremrangebyscore(
                full_key,
                "-inf",
                cutoff,
            )

            # Set expiry on the sorted set itself
            await redis_client.expire(full_key, self.metrics_ttl)

        except Exception as e:
            logger.error(f"Error adding timing {key}: {e}")

    async def track_cache_hit(self, cache_type: str = "rag_response") -> None:
        """Track cache hit."""
        await self._increment_counter(f"cache_hit:{cache_type}")

    async def track_cache_miss(self, cache_type: str = "rag_response") -> None:
        """Track cache miss."""
        await self._increment_counter(f"cache_miss:{cache_type}")

    async def track_search_latency(self, duration_ms: float) -> None:
        """Track vector search latency."""
        await self._add_timing("search_latency", duration_ms)

    async def track_llm_latency(self, duration_ms: float, provider: str) -> None:
        """Track LLM generation latency."""
        await self._add_timing(f"llm_latency:{provider}", duration_ms)

    async def track_query_complexity(self, complexity: str) -> None:
        """Track query complexity distribution."""
        await self._increment_counter(f"query_complexity:{complexity}")

    async def track_tokens_used(self, tokens: int, provider: str) -> None:
        """Track token usage."""
        await self._increment_counter(f"tokens_used:{provider}", tokens)

    @asynccontextmanager
    async def track_duration(self, metric_name: str):
        """
        Context manager to track operation duration.

        Usage:
            async with metrics.track_duration("search"):
                result = await search_operation()
        """
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            await self._add_timing(metric_name, duration_ms)

    async def get_cache_hit_rate(self, cache_type: str = "rag_response") -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0-100)
        """
        if not self.is_available:
            return 0.0

        redis_client = self.redis.client  # type: ignore[union-attr]
        if not redis_client:
            return 0.0

        try:
            hits = await redis_client.get(f"metrics:cache_hit:{cache_type}") or "0"
            misses = await redis_client.get(f"metrics:cache_miss:{cache_type}") or "0"

            total = int(hits) + int(misses)
            if total == 0:
                return 0.0

            hit_rate = (int(hits) / total) * 100
            return round(hit_rate, 2)

        except Exception as e:
            logger.error(f"Error calculating hit rate: {e}")
            return 0.0

    async def get_average_latency(self, metric_name: str) -> float:
        """
        Get average latency for a metric.

        Args:
            metric_name: Name of timing metric

        Returns:
            Average latency in milliseconds
        """
        if not self.is_available:
            return 0.0

        redis_client = self.redis.client  # type: ignore[union-attr]
        if not redis_client:
            return 0.0

        try:
            full_key = f"metrics:timing:{metric_name}"
            # Get all members from the sorted set
            members = await redis_client.zrange(full_key, 0, -1)

            if not members:
                return 0.0

            # Extract duration from timestamp:duration format
            latencies = []
            for member in members:
                try:
                    # member format: "timestamp:duration"
                    _, duration_str = member.split(":", 1)
                    latencies.append(float(duration_str))
                except (ValueError, IndexError):
                    continue

            if not latencies:
                return 0.0

            avg = sum(latencies) / len(latencies)
            return round(avg, 2)

        except Exception as e:
            logger.error(f"Error calculating average latency for {metric_name}: {e}")
            return 0.0

    async def get_percentile_latency(
        self,
        metric_name: str,
        percentile: float = 95.0,
    ) -> float:
        """
        Get percentile latency (e.g., P95, P99).

        Args:
            metric_name: Name of timing metric
            percentile: Percentile to calculate (0-100)

        Returns:
            Latency at percentile in milliseconds
        """
        if not self.is_available:
            return 0.0

        redis_client = self.redis.client  # type: ignore[union-attr]
        if not redis_client:
            return 0.0

        try:
            full_key = f"metrics:timing:{metric_name}"
            members = await redis_client.zrange(full_key, 0, -1)

            if not members:
                return 0.0

            # Extract and sort latencies
            latencies = []
            for member in members:
                try:
                    _, duration_str = member.split(":", 1)
                    latencies.append(float(duration_str))
                except (ValueError, IndexError):
                    continue

            if not latencies:
                return 0.0

            latencies.sort()

            # Calculate percentile index
            index = int((percentile / 100) * len(latencies))
            index = min(index, len(latencies) - 1)

            return round(latencies[index], 2)

        except Exception as e:
            logger.error(f"Error calculating percentile for {metric_name}: {e}")
            return 0.0

    async def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dict with all metrics
        """
        if not self.is_available:
            return {
                "enabled": False,
                "message": "Redis not available - metrics tracking disabled",
            }

        redis_client = self.redis.client  # type: ignore[union-attr]
        if not redis_client:
            return {
                "enabled": False,
                "message": "Redis client not available",
            }

        try:
            # Cache metrics
            cache_hit_rate = await self.get_cache_hit_rate("rag_response")
            embedding_hit_rate = await self.get_cache_hit_rate("embedding")

            # Latency metrics
            search_avg = await self.get_average_latency("search_latency")
            search_p95 = await self.get_percentile_latency("search_latency", 95)

            llm_anthropic_avg = await self.get_average_latency("llm_latency:anthropic")
            llm_ollama_avg = await self.get_average_latency("llm_latency:ollama")

            # Query complexity distribution
            simple_queries = int(await redis_client.get("metrics:query_complexity:simple") or "0")
            moderate_queries = int(
                await redis_client.get("metrics:query_complexity:moderate") or "0"
            )
            complex_queries = int(await redis_client.get("metrics:query_complexity:complex") or "0")

            total_queries = simple_queries + moderate_queries + complex_queries

            # Token usage
            anthropic_tokens = int(await redis_client.get("metrics:tokens_used:anthropic") or "0")
            ollama_tokens = int(await redis_client.get("metrics:tokens_used:ollama") or "0")

            return {
                "enabled": True,
                "cache": {
                    "rag_response_hit_rate": f"{cache_hit_rate}%",
                    "embedding_hit_rate": f"{embedding_hit_rate}%",
                },
                "latency": {
                    "search_avg_ms": search_avg,
                    "search_p95_ms": search_p95,
                    "llm_anthropic_avg_ms": llm_anthropic_avg,
                    "llm_ollama_avg_ms": llm_ollama_avg,
                },
                "query_complexity": {
                    "total": total_queries,
                    "simple": simple_queries,
                    "moderate": moderate_queries,
                    "complex": complex_queries,
                    "distribution": {
                        "simple_pct": round((simple_queries / total_queries * 100), 1)
                        if total_queries > 0
                        else 0,
                        "moderate_pct": round((moderate_queries / total_queries * 100), 1)
                        if total_queries > 0
                        else 0,
                        "complex_pct": round((complex_queries / total_queries * 100), 1)
                        if total_queries > 0
                        else 0,
                    },
                },
                "tokens": {
                    "anthropic": anthropic_tokens,
                    "ollama": ollama_tokens,
                    "total": anthropic_tokens + ollama_tokens,
                },
            }

        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {
                "enabled": True,
                "error": str(e),
            }
