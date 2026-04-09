"""
Shard Manager - Coordinates document sharding using consistent hashing.

Responsibilities:
- Manage shard nodes (database shards, storage shards)
- Route documents to correct shard based on hash
- Handle shard health and failover
- Provide shard discovery for queries
"""

import logging
from typing import Any

from app.core.consistent_hash import ConsistentHashRing, Node

logger = logging.getLogger(__name__)


class ShardManager:
    """
    Manages document sharding across multiple database/storage shards.

    Uses consistent hashing to:
    1. Distribute documents evenly across shards
    2. Minimize data movement when adding/removing shards
    3. Support shard failover
    """

    def __init__(self, virtual_nodes: int = 150):
        """
        Initialize shard manager.

        Args:
            virtual_nodes: Virtual nodes per shard for better distribution
        """
        self.ring = ConsistentHashRing(virtual_nodes_per_node=virtual_nodes)
        self._initialized = False

    def initialize_shards(self, shard_configs: list[dict[str, Any]]) -> None:
        """
        Initialize shards from configuration.

        Args:
            shard_configs: List of shard configurations
                          Each config: {"id": "shard-1", "weight": 1, "metadata": {...}}
        """
        for config in shard_configs:
            node = Node(
                id=config["id"],
                weight=config.get("weight", 1),
                metadata=config.get("metadata", {}),
                is_healthy=config.get("is_healthy", True),
            )
            self.ring.add_node(node)
            logger.info(f"Initialized shard: {node}")

        self._initialized = True
        logger.info(f"Shard manager initialized with {len(shard_configs)} shards")

    def get_shard_for_user(self, user_id: int) -> str | None:
        """
        Get shard ID for a user's documents.

        All documents for a user go to the same shard for:
        - Query efficiency (no cross-shard queries for user's docs)
        - Transaction consistency

        Args:
            user_id: User ID

        Returns:
            Shard ID, or None if no shards available
        """
        key = f"user:{user_id}"
        node = self.ring.get_node(key)
        return node.id if node else None

    def get_shard_for_document(self, document_id: int) -> str | None:
        """
        Get shard ID for a specific document.

        Alternative to user-based sharding. Use if you want to distribute
        individual documents rather than grouping by user.

        Args:
            document_id: Document ID

        Returns:
            Shard ID, or None if no shards available
        """
        key = f"doc:{document_id}"
        node = self.ring.get_node(key)
        return node.id if node else None

    def get_shard_for_key(self, key: str) -> str | None:
        """
        Get shard ID for an arbitrary key.

        Args:
            key: Any string key

        Returns:
            Shard ID, or None if no shards available
        """
        node = self.ring.get_node(key)
        return node.id if node else None

    def add_shard(
        self, shard_id: str, weight: int = 1, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Add a new shard to the ring.

        Args:
            shard_id: Unique shard identifier
            weight: Shard weight (higher = more keys)
            metadata: Additional shard metadata
        """
        node = Node(id=shard_id, weight=weight, metadata=metadata or {}, is_healthy=True)
        self.ring.add_node(node)
        logger.info(f"Added shard: {node}")

    def remove_shard(self, shard_id: str) -> None:
        """
        Remove a shard from the ring.

        Note: This will cause keys to be remapped to other shards.
        You should migrate data before removing a shard in production.

        Args:
            shard_id: Shard ID to remove
        """
        self.ring.remove_node(shard_id)
        logger.info(f"Removed shard: {shard_id}")

    def mark_shard_unhealthy(self, shard_id: str) -> None:
        """
        Mark a shard as unhealthy (for failover).

        Requests will be routed to next available healthy shard.

        Args:
            shard_id: Shard ID to mark unhealthy
        """
        self.ring.mark_node_unhealthy(shard_id)
        logger.warning(f"Marked shard {shard_id} as unhealthy")

    def mark_shard_healthy(self, shard_id: str) -> None:
        """
        Mark a shard as healthy (recovery).

        Args:
            shard_id: Shard ID to mark healthy
        """
        self.ring.mark_node_healthy(shard_id)
        logger.info(f"Marked shard {shard_id} as healthy")

    def get_all_shards(self) -> list[Node]:
        """Get all shards in the ring."""
        return self.ring.get_all_nodes()

    def get_healthy_shards(self) -> list[Node]:
        """Get all healthy shards."""
        return self.ring.get_healthy_nodes()

    def get_shard_info(self, shard_id: str) -> Node | None:
        """Get information about a specific shard."""
        return self.ring.get_node_by_id(shard_id)

    def get_distribution_report(self, num_test_keys: int = 10000) -> dict[str, Any]:
        """
        Generate distribution report for current shard configuration.

        Args:
            num_test_keys: Number of keys to test with

        Returns:
            Distribution statistics
        """
        return self.ring.get_distribution_stats(num_test_keys)

    def estimate_key_movement(
        self,
        test_keys: list[str],
        new_shard_id: str | None = None,
        removed_shard_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Estimate how many keys would move if a shard is added/removed.

        Args:
            test_keys: Sample keys to test
            new_shard_id: ID for new shard (if adding)
            removed_shard_id: ID of shard to remove (if removing)

        Returns:
            Movement statistics
        """
        if new_shard_id:
            new_node = Node(id=new_shard_id, weight=1)
            return self.ring.calculate_key_movement(test_keys, new_node=new_node)
        elif removed_shard_id:
            return self.ring.calculate_key_movement(test_keys, removed_node_id=removed_shard_id)
        else:
            return {"error": "Must specify either new_shard_id or removed_shard_id"}

    def is_initialized(self) -> bool:
        """Check if shard manager is initialized."""
        return self._initialized and self.ring.size() > 0


# Global shard manager instance
shard_manager = ShardManager()
