"""MemU client with local storage and LLM integration."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal

import numpy as np
from openai import AsyncOpenAI

from meow_agent.config import settings
from meow_agent.models import RetrievedContext
from meow_agent.memu.local_store import LocalMemoryStore


class MemUClient:
    """MemU client with three-layer memory architecture.

    In local mode, uses LocalMemoryStore (JSON files) for persistence.
    In cloud mode, would use MemU Cloud API.
    """

    def __init__(self, use_cloud: bool = False):
        """Initialize MemU client.

        Args:
            use_cloud: Whether to use MemU Cloud API.
        """
        self.use_cloud = use_cloud
        self.model = settings.dashscope_model

        # Initialize OpenAI-compatible LLM client
        self._llm = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )

        if use_cloud:
            # Cloud mode - would use MemU API
            self._store = None
            raise NotImplementedError("Cloud mode not yet implemented")
        else:
            # Local mode - use JSON file storage
            self._store = LocalMemoryStore(settings.memory_store_path)

        if settings.verbose:
            print(f"[MemU] Initialized in {'cloud' if use_cloud else 'local'} mode")
            print(f"[MemU] Storage path: {settings.memory_store_path}")

    async def close(self) -> None:
        """Close any open connections."""
        pass

    # ═══════════════════════════════════════════════════════════
    # High-level Memory Operations
    # ═══════════════════════════════════════════════════════════

    async def memorize_interaction(
        self,
        session_id: str,
        input_text: str,
        output_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a conversation interaction in memory.

        Args:
            session_id: Session identifier.
            input_text: User input text.
            output_text: Agent output text.
            metadata: Additional metadata.

        Returns:
            Resource ID.
        """
        timestamp = datetime.now(UTC).isoformat()

        # Layer 1: Create resource (raw conversation)
        resource = self._store.create_resource({
            "session_id": session_id,
            "type": "conversation",
            "content": {"input": input_text, "output": output_text},
            "metadata": metadata or {},
            "timestamp": timestamp,
        })
        resource_id = resource["id"]

        if settings.verbose:
            print(f"[MemU] Created resource: {resource_id}")

        # Layer 2: Extract memory items using LLM
        memory_items = await self._extract_memory_items(
            session_id, resource_id, input_text, output_text
        )

        if settings.verbose:
            print(f"[MemU] Extracted {len(memory_items)} memory items")

        return resource_id

    async def _extract_memory_items(
        self,
        session_id: str,
        resource_id: str,
        input_text: str,
        output_text: str,
    ) -> list[dict[str, Any]]:
        """Extract memory items from conversation using LLM.

        Args:
            session_id: Session identifier.
            resource_id: Resource ID.
            input_text: User input.
            output_text: Agent output.

        Returns:
            List of created memory items.
        """
        # Truncate long texts
        max_len = 500
        inp = input_text[:max_len] if len(input_text) > max_len else input_text
        out = output_text[:max_len] if len(output_text) > max_len else output_text

        extraction_prompt = f"""从以下对话中提取关键记忆项。返回JSON数组，每项包含：
- type: 类型，必须是以下之一：fact(事实), preference(偏好), skill(技能), intent(意图), todo(待办)
- content: 记忆内容（简洁的中文描述）
- confidence: 置信度(0-1)
- tags: 标签数组

对话：
用户: {inp}
助手: {out}

只返回JSON数组，不要其他内容。如果没有值得记忆的内容，返回空数组[]。
示例：
[{{"type": "fact", "content": "用户的名字是小明", "confidence": 0.95, "tags": ["name", "profile"]}}]"""

        try:
            response = await self._llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.choices[0].message.content or "[]"

            # Extract JSON array from response
            if "[" in content:
                content = content[content.find("[") : content.rfind("]") + 1]
            extractions = json.loads(content)

        except Exception as e:
            if settings.verbose:
                print(f"[MemU] LLM extraction failed: {e}")
            # Fallback: create a basic memory item
            extractions = [
                {
                    "type": "fact",
                    "content": f"用户说: {input_text[:80]}",
                    "confidence": 0.6,
                    "tags": ["auto", "conversation"],
                }
            ]

        # Create memory items with embeddings
        items = []
        for item_data in extractions:
            try:
                # Generate embedding for the content
                embedding = await self._get_embedding(item_data["content"])

                item = self._store.create_memory_item({
                    "resource_id": resource_id,
                    "type": item_data.get("type", "fact"),
                    "content": item_data["content"],
                    "embedding": embedding,
                    "confidence": item_data.get("confidence", 0.8),
                    "tags": item_data.get("tags", []),
                    "session_id": session_id,
                    "access_count": 0,
                })
                items.append(item)

            except Exception as e:
                if settings.verbose:
                    print(f"[MemU] Failed to create memory item: {e}")

        return items

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text.

        Uses a simple hash-based embedding as fallback.
        In production, would use a proper embedding model.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (64 dimensions).
        """
        try:
            # Try to use OpenAI embedding API if configured
            if settings.embedding_base_url and settings.embedding_api_key:
                embed_client = AsyncOpenAI(
                    api_key=settings.embedding_api_key,
                    base_url=settings.embedding_base_url,
                )
                response = await embed_client.embeddings.create(
                    model=settings.embedding_model,
                    input=text,
                )
                return response.data[0].embedding
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Embedding API failed, using hash fallback: {e}")

        # Fallback: deterministic hash-based embedding
        # This ensures same text always gets same embedding
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = [(hash_bytes[i % 32] - 128) / 128.0 for i in range(64)]
        return embedding

    # ═══════════════════════════════════════════════════════════
    # Retrieval Operations
    # ═══════════════════════════════════════════════════════════

    async def retrieve(
        self,
        query: str,
        session_id: str,
        mode: Literal["embedding", "llm_reading", "hybrid"] = "hybrid",
        top_k: int = 5,
    ) -> RetrievedContext:
        """Retrieve relevant memories.

        Args:
            query: Query string.
            session_id: Session identifier.
            mode: Retrieval mode.
            top_k: Number of results.

        Returns:
            Retrieved context.
        """
        if settings.verbose:
            print(f"[MemU] Retrieving memories for: {query[:50]}...")

        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)

            # Search for similar items
            results = self._store.search_items(
                query_embedding=query_embedding,
                top_k=top_k,
                min_confidence=0.3,
            )

            # Filter by session_id if needed
            # (In a production system, this would be done in the search)

            # Update access count for retrieved items
            for item in results:
                self._store.update_memory_item_access(item["id"])

            # Format results
            memory_items = []
            for item in results:
                memory_items.append({
                    "id": item["id"],
                    "type": item.get("type", "fact"),
                    "content": item.get("content", ""),
                    "confidence": item.get("confidence", 0.8),
                    "tags": item.get("tags", []),
                })

            if settings.verbose:
                print(f"[MemU] Found {len(memory_items)} relevant memories")

            return RetrievedContext(
                items=memory_items,
                llm_context="",  # Would be populated in LLM reading mode
            )

        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Retrieve failed: {e}")
            return RetrievedContext()

    # ═══════════════════════════════════════════════════════════
    # Memory Management Operations
    # ═══════════════════════════════════════════════════════════

    async def update_memory_item(
        self,
        memory_id: str,
        content: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Update a memory item."""
        try:
            embedding = await self._get_embedding(content)
            return self._store.update_memory_item(memory_id, {
                "content": content,
                "embedding": embedding,
            })
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Update failed: {e}")
            return None

    async def delete_memory_item(
        self,
        memory_id: str,
        session_id: str,
    ) -> bool:
        """Delete a memory item."""
        try:
            return self._store.delete_memory_item(memory_id)
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Delete failed: {e}")
            return False

    async def list_memory_items(
        self,
        session_id: str,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List memory items."""
        try:
            items = self._store.items
            if session_id != "all":
                items = [i for i in items if i.get("session_id") == session_id]
            if memory_type:
                items = [i for i in items if i.get("type") == memory_type]
            return items
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] List failed: {e}")
            return []

    async def clear_memory(self, session_id: str) -> bool:
        """Clear all memory for a session."""
        try:
            # Remove items for this session
            self._store.items = [
                i for i in self._store.items
                if i.get("session_id") != session_id
            ]
            self._store._save()
            return True
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Clear failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════
    # Analytics and Self-Evolution Operations
    # ═══════════════════════════════════════════════════════════

    async def get_hot_topics(
        self,
        min_access_count: int = 2,
        time_window: str = "7d",
        threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Get hot topics based on access frequency."""
        try:
            items = self._store.items
            hot_topics = []

            for item in items:
                access_count = item.get("access_count", 0)
                if access_count >= min_access_count:
                    hot_topics.append({
                        "name": item.get("content", "")[:50],
                        "access_count": access_count,
                        "relevance_score": min(1.0, access_count / 5.0),
                        "last_accessed": item.get("last_accessed"),
                        "item_id": item.get("id"),
                    })

            hot_topics.sort(key=lambda x: x["relevance_score"], reverse=True)
            return [t for t in hot_topics if t["relevance_score"] >= threshold]

        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Get hot topics failed: {e}")
            return []

    async def reorganize_if_needed(self) -> bool:
        """Check if memory reorganization is needed."""
        try:
            stats = self._store.get_fragmentation_stats()
            if stats["fragmentation_score"] > 0.8:
                if settings.verbose:
                    print("[MemU] Memory reorganization would be triggered")
                return True
            return False
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════
    # Debugging and Utilities
    # ═══════════════════════════════════════════════════════════

    def get_store_stats(self) -> dict[str, Any]:
        """Get statistics about the memory store."""
        return {
            "total_resources": len(self._store.resources),
            "total_items": len(self._store.items),
            "total_categories": len(self._store.categories),
            "store_path": settings.memory_store_path,
        }
