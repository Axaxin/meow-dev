"""Main agent for user interaction."""

import asyncio
from typing import Any

from openai import AsyncOpenAI

from meow_agent.config import settings
from meow_agent.event_bus import EventBus
from meow_agent.models import Event, EventType, Response, RetrievedContext
from meow_agent.memu.client import MemUClient


class MainAgent:
    """User-facing main agent that handles queries."""

    def __init__(
        self,
        memu_client: MemUClient,
        event_bus: EventBus | None = None,
    ):
        """Initialize the main agent.

        Args:
            memu_client: MemU client for memory operations.
            event_bus: Optional event bus for publishing events.
        """
        self.memu = memu_client
        self.event_bus = event_bus
        self.llm = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )
        self.model = settings.dashscope_model
        self._pending_tasks: list[asyncio.Task] = []

    async def wait_for_storage(self) -> None:
        """Wait for all pending memory storage tasks to complete."""
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()

    async def handle(
        self,
        user_query: str,
        session_id: str,
    ) -> Response:
        """Handle a user query.

        Args:
            user_query: The user's input query.
            session_id: Session identifier.

        Returns:
            Agent response.
        """
        # Publish user input event
        if self.event_bus:
            await self.event_bus.publish_user_input(session_id, user_query)

        # 1. Retrieve relevant memories (hybrid mode)
        memories = await self.memu.retrieve(
            query=user_query,
            session_id=session_id,
            mode="hybrid",
        )

        # 2. Build enhanced context
        context = self._build_context(user_query, memories)

        # 3. Generate response using LLM
        response_content = await self._generate_response(context)

        # 4. Create response object
        response = Response(
            content=response_content,
            session_id=session_id,
        )

        # 5. Publish agent output event (triggers memory storage)
        if self.event_bus:
            await self.event_bus.publish_agent_output(
                session_id,
                response_content,
                metadata={"query": user_query},
            )

        # 6. Store interaction asynchronously (non-blocking)
        task = asyncio.create_task(
            self.memu.memorize_interaction(
                session_id=session_id,
                input_text=user_query,
                output_text=response_content,
            )
        )
        self._pending_tasks.append(task)
        # Clean up completed tasks
        self._pending_tasks = [t for t in self._pending_tasks if not t.done()]

        return response

    def _build_context(
        self,
        user_query: str,
        memories: RetrievedContext,
    ) -> str:
        """Build enhanced context with retrieved memories.

        Args:
            user_query: User's query.
            memories: Retrieved memory context.

        Returns:
            Built context string.
        """
        parts = [f"用户问题: {user_query}"]

        # Add memory items context
        if memories.items:
            memory_parts = []
            for item in memories.items[:5]:  # Top 5 items
                memory_parts.append(
                    f"- [{item.get('type', 'unknown')}]: {item.get('content', '')}"
                )
            parts.append("\n相关记忆:")
            parts.extend(memory_parts)

        # Add LLM reading context
        if memories.llm_context:
            parts.append(f"\n深度记忆:\n{memories.llm_context}")

        return "\n".join(parts)

    async def _generate_response(self, context: str) -> str:
        """Generate response using LLM.

        Args:
            context: Built context string.

        Returns:
            Generated response.
        """
        system_prompt = """你是一个智能助手，具有长期记忆能力。你会根据用户的过往对话记忆来提供个性化的回答。
请用简洁、友好的语气回答用户的问题。如果用户询问之前说过的话，请从记忆中检索并准确回答。"""

        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            return response.choices[0].message.content or "抱歉，我暂时无法回答这个问题。"
        except Exception as e:
            if settings.verbose:
                print(f"Error generating response: {e}")
            return f"抱歉，生成回答时出现错误。请稍后再试。"

    async def chat(
        self,
        messages: list[dict[str, str]],
        session_id: str,
    ) -> str:
        """Multi-turn conversation with memory support.

        Args:
            messages: List of conversation messages.
            session_id: Session identifier.

        Returns:
            Agent response.
        """
        # Get last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        if last_user_message:
            response = await self.handle(last_user_message, session_id)
            return response.content

        return "请告诉我您想聊什么？"