"""Event bus for async pub/sub communication."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncIterator

from meow_agent.models import Event, EventType


class EventBus:
    """Async event bus for component communication."""

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._running = True

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Args:
            event: Event to publish.
        """
        event_type = event.type.value if isinstance(event.type, EventType) else event.type

        for queue in self._subscribers[event_type]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Skip if queue is full

        # Also publish to wildcard subscribers
        for queue in self._subscribers["*"]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(
        self,
        event_types: list[str | EventType] | None = None,
    ) -> AsyncIterator[Event]:
        """Subscribe to events.

        Args:
            event_types: Types of events to subscribe to. None means all events.

        Yields:
            Events matching the subscription.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        if event_types is None:
            self._subscribers["*"].append(queue)
        else:
            for et in event_types:
                event_type = et.value if isinstance(et, EventType) else et
                self._subscribers[event_type].append(queue)

        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    continue
        finally:
            # Cleanup
            if event_types is None:
                self._subscribers["*"].remove(queue)
            else:
                for et in event_types:
                    event_type = et.value if isinstance(et, EventType) else et
                    if queue in self._subscribers[event_type]:
                        self._subscribers[event_type].remove(queue)

    def stop(self) -> None:
        """Stop the event bus."""
        self._running = False

    async def publish_user_input(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish a user input event."""
        event = Event(
            type=EventType.USER_INPUT,
            data={"content": content, "metadata": metadata or {}},
            session_id=session_id,
        )
        await self.publish(event)

    async def publish_agent_output(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publish an agent output event."""
        event = Event(
            type=EventType.AGENT_OUTPUT,
            data={"content": content, "metadata": metadata or {}},
            session_id=session_id,
        )
        await self.publish(event)

    async def publish_proactive_suggestion(
        self,
        session_id: str,
        content: str,
        confidence: float = 0.8,
    ) -> None:
        """Publish a proactive suggestion event."""
        event = Event(
            type=EventType.PROACTIVE_SUGGESTION,
            data={"content": content, "confidence": confidence},
            session_id=session_id,
        )
        await self.publish(event)

    async def publish_tick(self, session_id: str = "system") -> None:
        """Publish a tick event for periodic tasks."""
        event = Event(
            type=EventType.TICK,
            data={},
            session_id=session_id,
        )
        await self.publish(event)