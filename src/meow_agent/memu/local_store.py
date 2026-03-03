"""Local JSON file storage for memory."""

import json
from pathlib import Path
from typing import Any

import numpy as np

from meow_agent.models import Category, MemoryItem, MemoryItemType, Resource


class LocalMemoryStore:
    """Local JSON storage for development and testing."""

    def __init__(self, path: str = "./memory_store"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        """Load all data from JSON files."""
        self.resources: list[dict[str, Any]] = self._read_json("resources.json", [])
        self.items: list[dict[str, Any]] = self._read_json("items.json", [])
        self.categories: list[dict[str, Any]] = self._read_json("categories.json", [])

    def _save(self) -> None:
        """Save all data to JSON files."""
        self._write_json("resources.json", self.resources)
        self._write_json("items.json", self.items)
        self._write_json("categories.json", self.categories)

    def _read_json(self, filename: str, default: Any) -> Any:
        """Read JSON file or return default."""
        filepath = self.path / filename
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        return default

    def _write_json(self, filename: str, data: Any) -> None:
        """Write data to JSON file."""
        filepath = self.path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════════════════════
    # Resource Layer CRUD
    # ═══════════════════════════════════════════════════════════

    def create_resource(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new resource."""
        resource_id = f"res_{len(self.resources) + 1:06d}"
        resource = {
            "id": resource_id,
            **data,
        }
        self.resources.append(resource)
        self._save()
        return resource

    def get_resource(self, resource_id: str) -> dict[str, Any] | None:
        """Get a resource by ID."""
        for resource in self.resources:
            if resource["id"] == resource_id:
                return resource
        return None

    def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource by ID."""
        for i, resource in enumerate(self.resources):
            if resource["id"] == resource_id:
                self.resources.pop(i)
                self._save()
                return True
        return False

    # ═══════════════════════════════════════════════════════════
    # Memory Item Layer CRUD + Vector Search
    # ═══════════════════════════════════════════════════════════

    def create_memory_item(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new memory item."""
        item_id = f"item_{len(self.items) + 1:06d}"
        item = {
            "id": item_id,
            **data,
        }
        self.items.append(item)
        self._save()
        return item

    def get_memory_item(self, item_id: str) -> dict[str, Any] | None:
        """Get a memory item by ID."""
        for item in self.items:
            if item["id"] == item_id:
                return item
        return None

    def update_memory_item_access(self, item_id: str) -> None:
        """Update access count and last_accessed for a memory item."""
        from datetime import UTC, datetime

        for item in self.items:
            if item["id"] == item_id:
                item["access_count"] = item.get("access_count", 0) + 1
                item["last_accessed"] = datetime.now(UTC).isoformat()
                self._save()
                return

    def search_items(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search memory items using cosine similarity.

        Filters out obsolete items automatically.
        """
        query = np.array(query_embedding)
        scored: list[tuple[float, dict[str, Any]]] = []

        for item in self.items:
            # Skip obsolete items
            if item.get("obsolete"):
                continue
            if item.get("confidence", 1.0) < min_confidence:
                continue
            emb = np.array(item.get("embedding", []))
            if len(emb) == 0:
                continue
            # Cosine similarity
            similarity = float(np.dot(query, emb) / (np.linalg.norm(query) * np.linalg.norm(emb)))
            scored.append((similarity, item))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def get_items_by_resource(self, resource_id: str) -> list[dict[str, Any]]:
        """Get all memory items for a resource."""
        return [item for item in self.items if item.get("resource_id") == resource_id]

    def get_items_by_type(self, item_type: str) -> list[dict[str, Any]]:
        """Get all memory items of a specific type."""
        return [item for item in self.items if item.get("type") == item_type]

    def update_memory_item(
        self, item_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update a memory item."""
        for item in self.items:
            if item["id"] == item_id:
                item.update(data)
                self._save()
                return item
        return None

    def delete_memory_item(self, item_id: str) -> bool:
        """Delete a memory item."""
        for i, item in enumerate(self.items):
            if item["id"] == item_id:
                self.items.pop(i)
                self._save()
                return True
        return False

    def mark_item_obsolete(self, item_id: str) -> bool:
        """Mark a memory item as obsolete/outdated."""
        for item in self.items:
            if item["id"] == item_id:
                item["obsolete"] = True
                item["confidence"] = 0.0  # Lower confidence so it won't be retrieved
                self._save()
                return True
        return False

    def find_similar_items(
        self,
        embedding: list[float],
        item_type: str | None = None,
        threshold: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Find items similar to the given embedding.

        Args:
            embedding: Query embedding vector.
            item_type: Optional type filter.
            threshold: Similarity threshold (0-1).

        Returns:
            List of similar items with similarity scores.
        """
        query = np.array(embedding)
        results = []

        for item in self.items:
            # Skip obsolete items
            if item.get("obsolete"):
                continue
            # Filter by type if specified
            if item_type and item.get("type") != item_type:
                continue

            emb = np.array(item.get("embedding", []))
            if len(emb) == 0:
                continue

            similarity = float(
                np.dot(query, emb) / (np.linalg.norm(query) * np.linalg.norm(emb))
            )
            if similarity >= threshold:
                results.append({"item": item, "similarity": similarity})

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    # ═══════════════════════════════════════════════════════════
    # Category Layer Management
    # ═══════════════════════════════════════════════════════════

    def create_category(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new category."""
        category_id = f"cat_{len(self.categories) + 1:06d}"
        category = {
            "id": category_id,
            **data,
        }
        self.categories.append(category)
        self._save()
        return category

    def get_category(self, category_id: str) -> dict[str, Any] | None:
        """Get a category by ID."""
        for category in self.categories:
            if category["id"] == category_id:
                return category
        return None

    def update_category(self, category_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a category."""
        for category in self.categories:
            if category["id"] == category_id:
                category.update(data)
                self._save()
                return category
        return None

    def add_item_to_category(self, category_id: str, item_id: str) -> bool:
        """Add a memory item to a category."""
        for category in self.categories:
            if category["id"] == category_id:
                if item_id not in category.get("item_ids", []):
                    category.setdefault("item_ids", []).append(item_id)
                    self._save()
                return True
        return False

    def get_relevant_categories(
        self, session_id: str, query_hint: str = ""
    ) -> list[dict[str, Any]]:
        """Get categories relevant to the session."""
        # Simple implementation: return all categories
        # Could be enhanced with semantic search
        return self.categories[:5]  # Return top 5 categories

    def get_hot_topics(
        self,
        min_access_count: int = 5,
        time_window: str = "7d",
        threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Get hot topics based on access frequency."""
        hot_items = [item for item in self.items if item.get("access_count", 0) >= min_access_count]
        return [
            {
                "name": item["content"][:50],
                "access_count": item.get("access_count", 0),
                "relevance_score": item.get("confidence", 0.5),
                "last_accessed": item.get("last_accessed"),
            }
            for item in hot_items
        ]

    def get_fragmentation_stats(self) -> dict[str, Any]:
        """Get fragmentation statistics for the memory."""
        return {
            "total_items": len(self.items),
            "total_categories": len(self.categories),
            "fragmentation_score": 0.0 if len(self.categories) < 10 else 0.5,
        }