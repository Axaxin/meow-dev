"""MemU Bot for memory extraction and proactive intelligence."""

import asyncio
import time
from typing import Any

from meow_agent.config import settings
from meow_agent.event_bus import EventBus
from meow_agent.models import Event, EventType
from meow_agent.memu.client import MemUClient


class MemUBot:
    """MemU-driven memory agent."""

    def __init__(
        self,
        memu_client: MemUClient,
        event_bus: EventBus,
    ):
        """Initialize the MemU Bot.

        Args:
            memu_client: MemU client for memory operations.
            event_bus: Event bus for subscribing to events.
        """
        self.memu = memu_client
        self.event_bus = event_bus
        self._running = False
        self._last_session_id: str | None = None
        self._last_proactive_time: float = 0.0

    async def monitor_loop(self) -> None:
        """Continuously monitor events and process them."""
        self._running = True

        # Subscribe to relevant events
        async for event in self.event_bus.subscribe(
            [EventType.USER_INPUT, EventType.AGENT_OUTPUT, EventType.TICK]
        ):
            if not self._running:
                break

            try:
                await self._process_event(event)
            except Exception as e:
                if settings.verbose:
                    print(f"Error processing event: {e}")

    async def _process_event(self, event: Event) -> None:
        """Process an event.

        Args:
            event: Event to process.
        """
        if event.type == EventType.USER_INPUT:
            await self._on_user_input(event)
        elif event.type == EventType.AGENT_OUTPUT:
            await self._on_agent_output(event)
        elif event.type == EventType.TICK:
            await self._run_proactive_tasks()

    async def _on_user_input(self, event: Event) -> None:
        """Handle user input event.

        Args:
            event: User input event.
        """
        self._last_session_id = event.session_id
        if settings.verbose:
            content = event.data.get("content", "")
            print(f"[MemUBot] User input: {content[:50]}...")

    async def _on_agent_output(self, event: Event) -> None:
        """Handle agent output event - extract and store memories.

        Args:
            event: Agent output event.
        """
        if settings.verbose:
            content = event.data.get("content", "")
            print(f"[MemUBot] Agent output: {content[:50]}...")

        # Memory extraction is already handled by MainAgent
        # Here we can do additional processing like intent prediction
        await self._predict_next_intent(event)

    async def _predict_next_intent(self, event: Event) -> None:
        """Predict the user's next intent based on the conversation.

        Args:
            event: Agent output event.
        """
        # Simple intent prediction based on hot topics
        hot_topics = await self.memu.get_hot_topics(threshold=0.5)

        if hot_topics and settings.verbose:
            top_topic = hot_topics[0]
            print(f"[MemUBot] Predicted hot topic: {top_topic.get('name', 'Unknown')}")

    async def _run_proactive_tasks(self) -> None:
        """Run proactive tasks periodically."""
        current_time = time.time()
        min_interval = max(settings.proactive_interval, 60)
        
        if current_time - self._last_proactive_time < min_interval:
            if settings.verbose:
                wait_time = int(min_interval - (current_time - self._last_proactive_time))
                print(f"[MemUBot] Skipping proactive tasks (next in {wait_time}s)")
            return
        
        self._last_proactive_time = current_time
        
        if settings.verbose:
            print("[MemUBot] Running proactive tasks...")

        try:
            hot_topics = await self.memu.get_hot_topics(threshold=0.7)

            for topic in hot_topics[:2]:
                confidence = topic.get("relevance_score", 0.5)
                if confidence > 0.8 and self._last_session_id:
                    suggestion = f"基于您之前的兴趣，您可能想继续了解: {topic.get('name', '相关话题')}"
                    await self.event_bus.publish_proactive_suggestion(
                        self._last_session_id,
                        suggestion,
                        confidence=confidence,
                    )

            await self.memu.reorganize_if_needed()
        except Exception as e:
            if settings.verbose:
                print(f"[MemUBot] Error in proactive tasks: {e}")

    def stop(self) -> None:
        """Stop the monitor loop."""
        self._running = False

    async def extract_and_store(
        self,
        session_id: str,
        input_text: str,
        output_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Manually trigger memory extraction and storage.

        Args:
            session_id: Session identifier.
            input_text: User input.
            output_text: Agent output.
            metadata: Additional metadata.

        Returns:
            Resource ID.
        """
        return await self.memu.memorize_interaction(
            session_id=session_id,
            input_text=input_text,
            output_text=output_text,
            metadata=metadata,
        )