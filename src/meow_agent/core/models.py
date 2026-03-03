"""Data models for the MemU agent."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedContext:
    """Context retrieved from memory."""

    items: list[dict[str, Any]] = field(default_factory=list)
    categories: list[dict[str, Any]] = field(default_factory=list)
    llm_context: str = ""
