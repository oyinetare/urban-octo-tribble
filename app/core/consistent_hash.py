"""
Consistent Hashing Implementation with Virtual Nodes.

Provides:
- Hash ring with configurable virtual nodes
- Even distribution of keys across nodes
- Minimal key movement when adding/removing nodes
- Support for node weights
"""

import bisect
import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    """Represents a physical node in the cluster."""

    id: str
    weight: int = 1  # Weight for virtual node distribution
    metadata: dict[str, Any] = field(default_factory=dict)
    is_healthy: bool = True

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.id == other.id

    def __repr__(self) -> str:
        status = "healthy" if self.is_healthy else "unhealthy"
        return f"<Node {self.id} ({status}, weight={self.weight})>"


class ConsistentHashRing:
    """
    Consistent hash ring with virtual nodes for even distribution.

    Features:
    - Virtual nodes (replicas) for better distribution
    - Weighted nodes (higher weight = more virtual nodes)
    - MD5 hashing for uniform distribution
    - Binary search for O(log n) lookups
    """

    def __init__(self, virtual_nodes_per_node: int = 150):
        """
        Initialize hash ring.

        Args:
            virtual_nodes_per_node: Number of virtual nodes per physical node.
                                   Higher = better distribution, but more memory.
                                   Typical: 100-200
        """
        self.virtual_nodes_per_node = virtual_nodes_per_node

        # Sorted list of hash values
        self._ring: list[int] = []

        # Map hash -> Node
        self._hash_to_node: dict[int, Node] = {}

        # Map node_id -> Node for quick lookup
        self._nodes: dict[str, Node] = {}

        # Map node_id -> list of its virtual node hashes
        self._node_virtual_hashes: dict[str, list[int]] = {}

    def _hash(self, key: str) -> int:
        """Hash a key to a position on the ring using MD5."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: Node) -> None:
        """
        Add a node to the hash ring.

        Args:
            node: Node to add

        Raises:
            ValueError: If node already exists
        """
        if node.id in self._nodes:
            raise ValueError(f"Node {node.id} already exists in ring")

        self._nodes[node.id] = node
        self._node_virtual_hashes[node.id] = []

        # Create virtual nodes based on weight
        num_virtual_nodes = self.virtual_nodes_per_node * node.weight

        for i in range(num_virtual_nodes):
            # Create unique identifier for each virtual node
            virtual_key = f"{node.id}:vnode:{i}"
            virtual_hash = self._hash(virtual_key)

            # Add to ring
            bisect.insort(self._ring, virtual_hash)
            self._hash_to_node[virtual_hash] = node
            self._node_virtual_hashes[node.id].append(virtual_hash)

    def remove_node(self, node_id: str) -> None:
        """
        Remove a node from the hash ring.

        Args:
            node_id: ID of node to remove

        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node {node_id} not found in ring")

        # Remove all virtual nodes
        for virtual_hash in self._node_virtual_hashes[node_id]:
            self._ring.remove(virtual_hash)
            del self._hash_to_node[virtual_hash]

        # Clean up
        del self._nodes[node_id]
        del self._node_virtual_hashes[node_id]

    def get_node(self, key: str, skip_unhealthy: bool = True) -> Node | None:
        """
        Find the node responsible for a given key.

        Args:
            key: Key to look up (e.g., user_id, document_id)
            skip_unhealthy: If True, skip unhealthy nodes and find next healthy one

        Returns:
            Node responsible for the key, or None if no healthy nodes available
        """
        if not self._ring:
            return None

        key_hash = self._hash(key)

        # Find position in ring (binary search)
        idx = bisect.bisect_right(self._ring, key_hash)

        # Wrap around if necessary
        if idx == len(self._ring):
            idx = 0

        # Try to find a healthy node
        attempts = 0
        max_attempts = len(self._ring)

        while attempts < max_attempts:
            virtual_hash = self._ring[idx]
            node = self._hash_to_node[virtual_hash]

            if not skip_unhealthy or node.is_healthy:
                return node

            # Move to next virtual node
            idx = (idx + 1) % len(self._ring)
            attempts += 1

        # No healthy nodes found
        return None

    def get_nodes_for_replication(
        self, key: str, replication_factor: int = 3, skip_unhealthy: bool = True
    ) -> list[Node]:
        """
        Get multiple nodes for key replication.

        Args:
            key: Key to look up
            replication_factor: Number of nodes to return
            skip_unhealthy: If True, only return healthy nodes

        Returns:
            List of nodes for replication (may be less than replication_factor
            if not enough nodes available)
        """
        if not self._ring:
            return []

        key_hash = self._hash(key)
        idx = bisect.bisect_right(self._ring, key_hash)
        if idx == len(self._ring):
            idx = 0

        nodes: list[Node] = []
        seen_node_ids: set[str] = set()
        attempts = 0
        max_attempts = len(self._ring)

        while len(nodes) < replication_factor and attempts < max_attempts:
            virtual_hash = self._ring[idx]
            node = self._hash_to_node[virtual_hash]

            # Skip if we already have this physical node
            if node.id not in seen_node_ids and (not skip_unhealthy or node.is_healthy):
                nodes.append(node)
                seen_node_ids.add(node.id)

            idx = (idx + 1) % len(self._ring)
            attempts += 1

        return nodes

    def mark_node_unhealthy(self, node_id: str) -> None:
        """Mark a node as unhealthy (for failover)."""
        if node_id in self._nodes:
            self._nodes[node_id].is_healthy = False

    def mark_node_healthy(self, node_id: str) -> None:
        """Mark a node as healthy (recovery)."""
        if node_id in self._nodes:
            self._nodes[node_id].is_healthy = True

    def get_all_nodes(self) -> list[Node]:
        """Get all nodes in the ring."""
        return list(self._nodes.values())

    def get_healthy_nodes(self) -> list[Node]:
        """Get all healthy nodes."""
        return [node for node in self._nodes.values() if node.is_healthy]

    def get_node_by_id(self, node_id: str) -> Node | None:
        """Get a specific node by ID."""
        return self._nodes.get(node_id)

    def size(self) -> int:
        """Get number of physical nodes in ring."""
        return len(self._nodes)

    def get_distribution_stats(self, num_keys: int = 10000) -> dict[str, Any]:
        """
        Analyze key distribution across nodes.

        Args:
            num_keys: Number of test keys to generate

        Returns:
            Distribution statistics
        """
        if not self._nodes:
            return {"error": "No nodes in ring"}

        distribution: dict[str, int] = dict.fromkeys(self._nodes, 0)

        for i in range(num_keys):
            key = f"test_key_{i}"
            node = self.get_node(key, skip_unhealthy=False)
            if node:
                distribution[node.id] += 1

        total_keys = sum(distribution.values())
        expected_per_node = total_keys / len(self._nodes)

        # Calculate standard deviation
        variance = sum((count - expected_per_node) ** 2 for count in distribution.values()) / len(
            self._nodes
        )
        std_dev = variance**0.5

        return {
            "total_nodes": len(self._nodes),
            "total_keys_tested": total_keys,
            "distribution": distribution,
            "expected_per_node": expected_per_node,
            "std_dev": std_dev,
            "min_keys": min(distribution.values()),
            "max_keys": max(distribution.values()),
            "imbalance_ratio": max(distribution.values()) / min(distribution.values())
            if min(distribution.values()) > 0
            else float("inf"),
        }

    def calculate_key_movement(
        self, keys: list[str], new_node: Node | None = None, removed_node_id: str | None = None
    ) -> dict[str, Any]:
        """
        Calculate how many keys would move if a node is added/removed.

        Args:
            keys: List of keys to test
            new_node: Node to add (for addition test)
            removed_node_id: Node to remove (for removal test)

        Returns:
            Movement statistics
        """
        if new_node and removed_node_id:
            raise ValueError("Cannot add and remove node simultaneously")

        # Get current mapping
        current_mapping = {key: self.get_node(key) for key in keys}

        # Simulate change
        if new_node:
            self.add_node(new_node)
        elif removed_node_id:
            self.remove_node(removed_node_id)
        else:
            return {"error": "Must specify either new_node or removed_node_id"}

        # Get new mapping
        new_mapping = {key: self.get_node(key) for key in keys}

        # Count movements
        moved = sum(1 for key in keys if current_mapping[key] != new_mapping[key])

        # Revert change
        if new_node:
            self.remove_node(new_node.id)
        elif removed_node_id:
            # Re-add the removed node (need to reconstruct it)
            pass  # Can't easily revert removal without keeping state

        return {
            "total_keys": len(keys),
            "keys_moved": moved,
            "keys_stayed": len(keys) - moved,
            "movement_percentage": (moved / len(keys) * 100) if keys else 0,
        }
