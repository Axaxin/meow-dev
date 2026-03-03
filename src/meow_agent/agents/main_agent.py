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
        if self.event_bus:
            await self.event_bus.publish_user_input(session_id, user_query)

        await self.wait_for_storage()

        memories = await self.memu.retrieve(
            query=user_query,
            session_id=session_id,
            mode="hybrid",
        )

        context = self._build_context(user_query, memories)

        response_content = await self._generate_response(context)

        response = Response(
            content=response_content,
            session_id=session_id,
        )

        if self.event_bus:
            await self.event_bus.publish_agent_output(
                session_id,
                response_content,
                metadata={"query": user_query},
            )

        task = asyncio.create_task(
            self.memu.memorize_interaction(
                session_id=session_id,
                input_text=user_query,
                output_text=response_content,
            )
        )
        self._pending_tasks.append(task)
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

        # Add memory items context (memU format)
        if memories.items:
            memory_parts = []
            for item in memories.items[:5]:  # Top 5 items
                memory_type = item.get("memory_type", "unknown")
                summary = item.get("summary", "")
                if summary:
                    memory_parts.append(
                        f"- [{memory_type}]: {summary}"
                    )
            if memory_parts:
                parts.append("\n相关记忆:")
                parts.extend(memory_parts)

        # Add category context
        if memories.categories:
            category_parts = []
            for cat in memories.categories[:3]:  # Top 3 categories
                name = cat.get("name", "")
                summary = cat.get("summary", "")
                if summary:
                    category_parts.append(
                        f"- [{name}]: {summary[:200]}"
                    )
            if category_parts:
                parts.append("\n相关类别:")
                parts.extend(category_parts)

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

重要规则：
1. 用简洁、友好的语气回答（控制在100字以内）
2. 不要重复用户已经知道的信息
3. 直接回答问题，不要过度展开
4. 如果用户询问之前说过的话，从记忆中检索并准确回答"""

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
                import traceback
                traceback.print_exc()
            else:
                error_msg = str(e)
                if "api_key" in error_msg.lower() or "401" in error_msg or "Unauthorized" in error_msg:
                    return "错误：API Key 未配置或无效。请在 .env 文件中设置 DASHSCOPE_API_KEY。"
                elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    return "错误：无法连接到 API 服务器。请检查网络连接和 BASE_URL 配置。"
            return "抱歉，生成回答时出现错误。请稍后再试。"

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