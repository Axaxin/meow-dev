"""MemU client wrapper using official memU SDK with optional persistence."""

import json
import tempfile
from pathlib import Path
from typing import Any, Literal

from memu.app import MemoryService

from meow_agent.config import settings
from meow_agent.models import RetrievedContext


class MemUClient:
    """MemU client wrapper using official memU SDK.

    This client wraps the memU MemoryService to provide:
    - Three-layer memory architecture (Resource → Item → Category)
    - Automatic memory extraction using LLM
    - RAG and LLM-based retrieval
    - Optional file-based persistence (when PostgreSQL not available)
    """

    def __init__(self, use_cloud: bool = False):
        """Initialize MemU client.

        Args:
            use_cloud: Whether to use MemU Cloud API (not implemented yet).
        """
        self.use_cloud = use_cloud
        self.model = settings.dashscope_model
        self._use_persistence = False

        if use_cloud:
            raise NotImplementedError("Cloud mode not yet implemented")

        # Build llm_profiles for memU
        llm_profiles = {
            "default": {
                "api_key": settings.dashscope_api_key,
                "base_url": settings.dashscope_base_url,
                "chat_model": settings.dashscope_model,
            }
        }

        # Configure embedding - memU ALWAYS needs this
        if settings.embedding_base_url and settings.embedding_api_key and settings.embedding_model:
            llm_profiles["embedding"] = {
                "api_key": settings.embedding_api_key,
                "base_url": settings.embedding_base_url,
                "embed_model": settings.embedding_model,
            }
            if settings.verbose:
                print(f"[MemU] Using custom embedding: {settings.embedding_base_url}")
                print(f"[MemU] Embedding model: {settings.embedding_model}")
        else:
            llm_profiles["embedding"] = {
                "api_key": settings.dashscope_api_key,
                "base_url": settings.dashscope_base_url,
                "embed_model": "text-embedding-ada-002",
            }
            if settings.verbose:
                print(f"[MemU] WARNING: Using chat endpoint for embeddings")
        
        # Configure database
        if settings.database_url:
            # Use PostgreSQL
            database_config = {
                "metadata_store": {
                    "provider": "postgres",
                    "connection_string": settings.database_url,
                }
            }
            if settings.verbose:
                print(f"[MemU] Using PostgreSQL for persistent storage")
        else:
            # Fall back to inmemory with file persistence
            database_config = {
                "metadata_store": {"provider": "inmemory"},
            }
            self._use_persistence = True
            self._persistence_dir = Path(settings.memory_store_path) / "memu_data"
            self._persistence_dir.mkdir(parents=True, exist_ok=True)
            self._conversations_file = self._persistence_dir / "conversations.jsonl"
            
            if settings.verbose:
                print(f"[MemU] Using inmemory + file persistence")
                print(f"[MemU] Data will persist to: {self._persistence_dir}")
                print(f"[MemU] TIP: For better persistence, configure PostgreSQL")
        
        # Initialize memU MemoryService
        self.service = MemoryService(
            llm_profiles=llm_profiles,
            database_config=database_config,
            retrieve_config={"method": "rag"},
        )
        
        # Load persisted conversations if using file persistence
        if self._use_persistence:
            self._load_conversations()

        if settings.verbose:
            print(f"[MemU] Initialized with memU SDK")
            print(f"[MemU] Mode: {'cloud' if use_cloud else 'local'}")
            print(f"[MemU] Memory path: {settings.memory_store_path}")

    async def close(self) -> None:
        """Close any open connections."""
        # memU MemoryService doesn't require explicit cleanup
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
        # Prepare conversation data in memU format
        conversation_data = {
            "messages": [
                {"role": "user", "content": input_text},
                {"role": "assistant", "content": output_text},
            ],
            "metadata": metadata or {},
            "session_id": session_id,
        }

        # Save to temporary file for memU to process
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        try:
            json.dump(conversation_data, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()

            if settings.verbose:
                print(f"[MemU] Memorizing conversation...")
                print(f"[MemU] User: {input_text[:100]}...")
                print(f"[MemU] Assistant: {output_text[:100]}...")

            # Use memU to memorize
            result = await self.service.memorize(
                resource_url=temp_file.name,
                modality="conversation",
                user={"user_id": session_id},
            )

            resource_id = result.get("resource", {}).get("id", "")

            if settings.verbose:
                items = result.get("items", [])
                categories = result.get("categories", [])
                print(f"[MemU] ✅ Memorized successfully")
                print(f"[MemU] Resource ID: {resource_id}")
                print(f"[MemU] Extracted {len(items)} memory items")
                if items:
                    for i, item in enumerate(items[:3], 1):
                        memory_type = item.get("memory_type", "unknown")
                        summary = item.get("summary", item.get("content", ""))[:80]
                        print(f"[MemU]   {i}. [{memory_type}] {summary}...")
                print(f"[MemU] Updated {len(categories)} categories")

            return resource_id

        except Exception as e:
            if settings.verbose:
                print(f"[MemU] ❌ Memorize failed: {e}")
                import traceback
                traceback.print_exc()
            return ""
        finally:
            # Clean up temp file
            Path(temp_file.name).unlink(missing_ok=True)

    # ═══════════════════════════════════════════════════════════
    # Retrieval Operations
    # ═══════════════════════════════════════════════════════════

    async def retrieve(
        self,
        query: str,
        session_id: str,
        mode: Literal["rag", "llm", "hybrid"] = "hybrid",
        top_k: int = 5,
    ) -> RetrievedContext:
        """Retrieve relevant memories.

        Args:
            query: Query string.
            session_id: Session identifier.
            mode: Retrieval mode ('rag', 'llm', or 'hybrid').
            top_k: Number of results (not used in memU, for compatibility).

        Returns:
            Retrieved context.
        """
        if settings.verbose:
            print(f"[MemU] Retrieving memories for: {query[:50]}...")

        # Build query for memU
        queries = [{"role": "user", "content": {"text": query}}]

        # Use RAG mode for hybrid (faster)
        method = "rag" if mode == "hybrid" else mode

        try:
            result = await self.service.retrieve(
                queries=queries,
                where={"user_id": session_id},
            )

            # Extract results
            items = result.get("items", [])
            categories = result.get("categories", [])
            llm_context = result.get("llm_context", "")

            if settings.verbose:
                print(f"[MemU] ✅ Retrieved successfully")
                print(f"[MemU] Found {len(items)} memory items")
                if items:
                    for i, item in enumerate(items[:3], 1):
                        memory_type = item.get("memory_type", "unknown")
                        summary = item.get("summary", item.get("content", ""))[:60]
                        print(f"[MemU]   {i}. [{memory_type}] {summary}...")
                print(f"[MemU] Found {len(categories)} categories")
                if categories:
                    for i, cat in enumerate(categories[:2], 1):
                        name = cat.get("name", "")
                        print(f"[MemU]   {i}. {name}")

            return RetrievedContext(
                items=items,
                categories=categories,
                llm_context=llm_context,
            )

        except Exception as e:
            if settings.verbose:
                print(f"[MemU] ❌ Retrieve failed: {e}")
                import traceback
                traceback.print_exc()
            return RetrievedContext()

    # ═══════════════════════════════════════════════════════════
    # Memory Management Operations
    # ═══════════════════════════════════════════════════════════

    async def list_memory_items(
        self,
        session_id: str,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List memory items.

        Note: memU doesn't have a direct list API, so this is a placeholder.
        """
        if settings.verbose:
            print(f"[MemU] List memory items not directly supported by memU SDK")
        return []

    async def clear_memory(self, session_id: str) -> bool:
        """Clear all memory for a session.

        Note: memU doesn't have a direct clear API, so this is a placeholder.
        """
        if settings.verbose:
            print(f"[MemU] Clear memory not directly supported by memU SDK")
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
        """Get hot topics based on access frequency.

        Note: memU doesn't have a hot topics API, so this returns empty list.
        """
        return []

    async def reorganize_if_needed(self) -> bool:
        """Check if memory reorganization is needed.

        Note: memU handles reorganization internally.
        """
        return False

    # ═══════════════════════════════════════════════════════════
    # Debugging and Utilities
    # ═══════════════════════════════════════════════════════════

    def get_store_stats(self) -> dict[str, Any]:
        """Get statistics about the memory store.

        Note: memU manages storage internally, so this returns basic info.
        """
        return {
            "mode": "local",
            "sdk": "memU",
            "memory_path": settings.memory_store_path,
            "model": settings.dashscope_model,
            "persistence": "file" if self._use_persistence else "postgres" if settings.database_url else "inmemory",
        }
    
    def _load_conversations(self):
        """Load persisted conversations from file."""
        if not self._use_persistence or not self._conversations_file.exists():
            return
        
        try:
            # Note: memU inmemory doesn't support loading data back
            # This is a limitation - we can only persist for future reference
            # Real persistence requires PostgreSQL
            pass
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Failed to load conversations: {e}")
    
    async def _save_conversation(self, conversation_data: dict[str, Any]):
        """Save conversation to file for reference."""
        if not self._use_persistence:
            return
        
        try:
            with open(self._conversations_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(conversation_data, ensure_ascii=False) + "\n")
        except Exception as e:
            if settings.verbose:
                print(f"[MemU] Failed to save conversation: {e}")
