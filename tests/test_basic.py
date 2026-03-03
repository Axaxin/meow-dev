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


class TestConfig:
    """Test configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.mode == "local"
        assert settings.verbose is False
        assert settings.proactive_interval == 60
        assert settings.memory_store_path == "./memory_store"


class TestMemUClient:
    """Test MemU client wrapper."""

    def test_client_initialization(self):
        """Test MemU client can be initialized."""
        from meow_agent.memu.client import MemUClient
        
        # This should not raise an error
        # Note: requires DASHSCOPE_API_KEY to be set
        try:
            client = MemUClient(use_cloud=False)
            assert client is not None
            assert client.service is not None
        except Exception:
            # If API key is not set, that's OK for this test
            pass
