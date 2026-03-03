"""Data models for the MemU agent."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now_iso() -> str:
    """Get current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


class MemoryItemType(str, Enum):
    """Types of memory items."""

    FACT = "fact"
    PREFERENCE = "preference"
    SKILL = "skill"
    INTENT = "intent"
    TODO = "todo"


class EventType(str, Enum):
    """Types of events in the event bus."""

    USER_INPUT = "user_input"
    AGENT_OUTPUT = "agent_output"
    PROACTIVE_SUGGESTION = "proactive_suggestion"
    TICK = "tick"


@dataclass
class Resource:
    """Layer 1: Raw multimodal data storage."""

    id: str
    type: str
    content: dict[str, Any]
    session_id: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_format: str = "text"


@dataclass
class MemoryItem:
    """Layer 2: Fine-grained memory extraction."""

    id: str
    resource_id: str
    type: MemoryItemType
    content: str
    embedding: list[float] = field(default_factory=list)
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: str | None = None
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass
class Category:
    """Layer 3: Thematic organization of memory items."""

    id: str
    name: str
    description: str
    consolidated_content: str = ""
    item_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    last_updated: str = field(default_factory=_utc_now_iso)
    access_frequency: str = "medium"  # low, medium, high


@dataclass
class Event:
    """Event for the event bus."""

    type: EventType
    data: dict[str, Any]
    session_id: str
    timestamp: str = field(default_factory=_utc_now_iso)


@dataclass
class Response:
    """Response from the main agent."""

    content: str
    session_id: str
    proactive_suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedContext:
    """Context retrieved from memory."""

    items: list[MemoryItem] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)
    llm_context: str = ""


@dataclass
class HotTopic:
    """Hot topic for proactive suggestions."""

    name: str
    access_count: int
    relevance_score: float
    last_accessed: str