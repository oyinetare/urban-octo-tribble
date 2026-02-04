"""
Shard service for managing shard lifecycle and health.

Responsibilities:
- Initialize shards from configuration
- Periodic health checks
- Automatic failover on unhealthy shards
- Shard metrics and monitoring
"""

import asyncio
import contextlib
import logging
from typing import Any

from app.core.config import get_settings
from app.core.shard_manager import shard_manager
from app.utility import utc_now

logger = logging.getLogger(__name__)
settings = get_settings()


class ShardService:
    """
    Service for managing shard infrastructure.

    Features:
    - Auto-initialization from config
    - Health check scheduling
    - Metrics collection
    - Failover coordination
    """

    def __init__(self):
        self.health_check_interval = 30  # seconds
        self.health_check_task: asyncio.Task | None = None
        self._shard_health_history: dict[str, list[dict[str, Any]]] = {}

    async def initialize(self) -> None:
        """Initialize shards from configuration."""
        if not settings.SHARDING_ENABLED:
            logger.info("Sharding is disabled in configuration")
            return

        try:
            # Parse shard configuration
            # Format: "shard-0:1,shard-1:1,shard-2:2"
            shard_configs = self._parse_shard_config(settings.SHARD_NODES)

            if not shard_configs:
                logger.warning("No shard nodes configured, using single default shard")
                shard_configs = [{"id": "shard-0", "weight": 1}]

            # Initialize shard manager
            shard_manager.initialize_shards(shard_configs)

            logger.info(
                f"✅ Shard service initialized with {len(shard_configs)} shards "
                f"(strategy: {settings.SHARDING_STRATEGY})"
            )

            # Log distribution stats
            stats = shard_manager.get_distribution_report()
            logger.info(f"📊 Distribution test (10k keys): {stats}")

            # Start health checks
            await self.start_health_checks()

        except Exception as e:
            logger.error(f"❌ Failed to initialize shard service: {e}")
            raise

    def _parse_shard_config(self, config_str: str) -> list[dict[str, Any]]:
        """
        Parse shard configuration string.

        Args:
            config_str: Format "id:weight,id:weight,..."
                       Example: "shard-0:1,shard-1:1,shard-2:2"

        Returns:
            List of shard configurations
        """
        configs = []

        for shard_spec in config_str.split(","):
            shard_spec = shard_spec.strip()
            if not shard_spec:
                continue

            parts = shard_spec.split(":")
            if len(parts) != 2:
                logger.warning(f"Invalid shard spec: {shard_spec}, expected 'id:weight'")
                continue

            shard_id, weight_str = parts
            try:
                weight = int(weight_str)
            except ValueError:
                logger.warning(f"Invalid weight for shard {shard_id}: {weight_str}")
                weight = 1

            configs.append(
                {
                    "id": shard_id.strip(),
                    "weight": weight,
                    "metadata": {"initialized_at": utc_now().isoformat()},
                }
            )

        return configs

    async def start_health_checks(self) -> None:
        """Start periodic health check background task."""
        if self.health_check_task is not None:
            logger.warning("Health checks already running")
            return

        logger.info(f"Starting shard health checks (interval: {self.health_check_interval}s)")
        self.health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self) -> None:
        """Stop health check background task."""
        if self.health_check_task:
            self.health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_check_task
            self.health_check_task = None
            logger.info("Stopped shard health checks")

    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.check_shard_health()
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def check_shard_health(self) -> dict[str, Any]:
        """
        Check health of all shards.

        In production, this would:
        - Ping database shards
        - Check storage availability
        - Verify network connectivity
        - Monitor response times

        Returns:
            Health check results
        """
        results = {}
        all_shards = shard_manager.get_all_shards()

        for shard in all_shards:
            is_healthy = await self._check_individual_shard(shard.id)

            # Update shard health
            if is_healthy and not shard.is_healthy:
                shard_manager.mark_shard_healthy(shard.id)
                logger.info(f"✅ Shard {shard.id} recovered")
            elif not is_healthy and shard.is_healthy:
                shard_manager.mark_shard_unhealthy(shard.id)
                logger.error(f"❌ Shard {shard.id} failed health check")

            results[shard.id] = {
                "is_healthy": is_healthy,
                "checked_at": utc_now().isoformat(),
            }

            # Track history
            if shard.id not in self._shard_health_history:
                self._shard_health_history[shard.id] = []

            self._shard_health_history[shard.id].append(results[shard.id])

            # Keep only last 100 checks
            if len(self._shard_health_history[shard.id]) > 100:
                self._shard_health_history[shard.id] = self._shard_health_history[shard.id][-100:]

        return results

    async def _check_individual_shard(self, _shard_id: str) -> bool:
        """
        Check if a specific shard is healthy.

        In production, implement actual health checks:
        - Database connectivity
        - Storage availability
        - Response time thresholds

        For now, always returns True (mock implementation).

        Args:
            shard_id: Shard to check

        Returns:
            True if healthy, False otherwise
        """
        # TODO: Implement actual health checks
        # Example:
        # - Try connecting to database
        # - Ping storage service
        # - Check response time

        # Mock: Randomly fail 5% of checks for testing
        # In production, remove this and implement real checks
        import random

        return random.random() > 0.05

    def get_shard_stats(self) -> dict[str, Any]:
        """
        Get current shard statistics.

        Returns:
            Shard statistics including health, distribution, etc.
        """
        all_shards = shard_manager.get_all_shards()
        healthy_shards = shard_manager.get_healthy_shards()

        return {
            "total_shards": len(all_shards),
            "healthy_shards": len(healthy_shards),
            "unhealthy_shards": len(all_shards) - len(healthy_shards),
            "shards": [
                {
                    "id": shard.id,
                    "is_healthy": shard.is_healthy,
                    "weight": shard.weight,
                    "metadata": shard.metadata,
                    "recent_health_checks": self._shard_health_history.get(shard.id, [])[-10:],
                }
                for shard in all_shards
            ],
            "distribution": shard_manager.get_distribution_report(),
            "strategy": settings.SHARDING_STRATEGY,
            "virtual_nodes": settings.SHARDING_VIRTUAL_NODES,
        }

    async def add_shard(
        self, shard_id: str, weight: int = 1, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Add a new shard to the cluster.

        Args:
            shard_id: Unique shard identifier
            weight: Shard weight (higher = more load)
            metadata: Additional shard metadata

        Returns:
            Result of adding shard including migration stats
        """
        # Estimate impact before adding
        test_keys = [f"user:{i}" for i in range(10000)]
        movement_before = shard_manager.estimate_key_movement(test_keys, new_shard_id=shard_id)

        # Add shard
        shard_manager.add_shard(shard_id, weight, metadata)

        logger.info(
            f"Added shard {shard_id} (weight: {weight}). "
            f"Estimated key movement: {movement_before['movement_percentage']:.2f}%"
        )

        return {
            "shard_id": shard_id,
            "weight": weight,
            "added_at": utc_now().isoformat(),
            "estimated_impact": movement_before,
        }

    async def remove_shard(self, shard_id: str) -> dict[str, Any]:
        """
        Remove a shard from the cluster.

        WARNING: This will cause keys to be remapped.
        Migrate data before removing in production.

        Args:
            shard_id: Shard to remove

        Returns:
            Result of removal
        """
        # Check if shard exists
        shard_info = shard_manager.get_shard_info(shard_id)
        if not shard_info:
            raise ValueError(f"Shard {shard_id} not found")

        # Remove shard
        shard_manager.remove_shard(shard_id)

        logger.warning(f"Removed shard {shard_id}")

        return {
            "shard_id": shard_id,
            "removed_at": utc_now().isoformat(),
            "warning": "Data may need to be migrated to new shards",
        }


# Global shard service instance
shard_service = ShardService()
