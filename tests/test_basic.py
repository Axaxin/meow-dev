"""Basic tests for meow-agent."""

import pytest

from meow_agent.config import Settings
from meow_agent.models import (
    Category,
    Event,
    EventType,
    MemoryItem,
    MemoryItemType,
    Resource,
    Response,
    RetrievedContext,
)
from meow_agent.memu.local_store import LocalMemoryStore


class TestModels:
    """Test data models."""

    def test_memory_item_type(self):
        """Test MemoryItemType enum."""
        assert MemoryItemType.FACT.value == "fact"
        assert MemoryItemType.PREFERENCE.value == "preference"
        assert MemoryItemType.SKILL.value == "skill"

    def test_event_type(self):
        """Test EventType enum."""
        assert EventType.USER_INPUT.value == "user_input"
        assert EventType.AGENT_OUTPUT.value == "agent_output"

    def test_resource(self):
        """Test Resource dataclass."""
        resource = Resource(
            id="res_001",
            type="conversation",
            content={"input": "hello", "output": "hi"},
            session_id="session_1",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert resource.id == "res_001"
        assert resource.type == "conversation"
        assert resource.content["input"] == "hello"

    def test_memory_item(self):
        """Test MemoryItem dataclass."""
        item = MemoryItem(
            id="item_001",
            resource_id="res_001",
            type=MemoryItemType.FACT,
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
            confidence=0.9,
            tags=["test"],
        )
        assert item.id == "item_001"
        assert item.type == MemoryItemType.FACT
        assert item.confidence == 0.9

    def test_category(self):
        """Test Category dataclass."""
        category = Category(
            id="cat_001",
            name="Test Category",
            description="Test description",
            item_ids=["item_001"],
        )
        assert category.id == "cat_001"
        assert category.name == "Test Category"
        assert "item_001" in category.item_ids

    def test_event(self):
        """Test Event dataclass."""
        event = Event(
            type=EventType.USER_INPUT,
            data={"content": "hello"},
            session_id="session_1",
        )
        assert event.type == EventType.USER_INPUT
        assert event.data["content"] == "hello"

    def test_response(self):
        """Test Response dataclass."""
        response = Response(
            content="Hello!",
            session_id="session_1",
        )
        assert response.content == "Hello!"
        assert response.session_id == "session_1"

    def test_retrieved_context(self):
        """Test RetrievedContext dataclass."""
        context = RetrievedContext(
            items=[],
            llm_context="test context",
        )
        assert context.items == []
        assert context.llm_context == "test context"


class TestLocalMemoryStore:
    """Test local memory store."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a local memory store."""
        return LocalMemoryStore(str(tmp_path / "memory_store"))

    def test_create_resource(self, store):
        """Test creating a resource."""
        resource = store.create_resource({
            "session_id": "session_1",
            "type": "conversation",
            "content": {"input": "hello", "output": "hi"},
        })
        assert resource["id"].startswith("res_")
        assert resource["session_id"] == "session_1"

    def test_get_resource(self, store):
        """Test getting a resource."""
        created = store.create_resource({
            "session_id": "session_1",
            "type": "conversation",
            "content": {},
        })
        retrieved = store.get_resource(created["id"])
        assert retrieved is not None
        assert retrieved["id"] == created["id"]

    def test_create_memory_item(self, store):
        """Test creating a memory item."""
        item = store.create_memory_item({
            "resource_id": "res_001",
            "type": "fact",
            "content": "Test content",
            "embedding": [0.1, 0.2, 0.3],
            "confidence": 0.9,
            "tags": ["test"],
        })
        assert item["id"].startswith("item_")
        assert item["content"] == "Test content"

    def test_search_items(self, store):
        """Test searching memory items."""
        # Create items with different embeddings
        store.create_memory_item({
            "resource_id": "res_001",
            "type": "fact",
            "content": "Python programming",
            "embedding": [1.0, 0.0, 0.0],
            "confidence": 0.9,
        })
        store.create_memory_item({
            "resource_id": "res_002",
            "type": "fact",
            "content": "JavaScript programming",
            "embedding": [0.0, 1.0, 0.0],
            "confidence": 0.9,
        })

        # Search with query similar to first item
        results = store.search_items([0.9, 0.1, 0.0], top_k=1)
        assert len(results) == 1
        assert "Python" in results[0]["content"]

    def test_create_category(self, store):
        """Test creating a category."""
        category = store.create_category({
            "name": "Programming",
            "description": "Programming related memories",
        })
        assert category["id"].startswith("cat_")
        assert category["name"] == "Programming"

    def test_add_item_to_category(self, store):
        """Test adding an item to a category."""
        item = store.create_memory_item({
            "resource_id": "res_001",
            "type": "fact",
            "content": "Test",
            "embedding": [],
        })
        category = store.create_category({
            "name": "Test Category",
            "description": "Test",
        })

        result = store.add_item_to_category(category["id"], item["id"])
        assert result is True

        updated = store.get_category(category["id"])
        assert item["id"] in updated["item_ids"]


class TestConfig:
    """Test configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.mode == "local"
        assert settings.verbose is False
        assert settings.proactive_interval == 60
        assert settings.memory_store_path == "./memory_store"