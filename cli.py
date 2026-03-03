#!/usr/bin/env python3
"""独立的 CLI 客户端，调用 MemU Service API"""

import asyncio
import requests
from openai import AsyncOpenAI
from prompt_toolkit import PromptSession

# ============ 配置（写死） ============
MEMU_SERVICE_URL = "http://localhost:8000"
DASHSCOPE_API_KEY = "sk-sp-c80db8b082a64256b3ed03a7876cda08"  # TODO: 替换为你的 API key
DASHSCOPE_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
DASHSCOPE_MODEL = "qwen3.5-plus"  # 可替换为你想使用的模型
SESSION_ID = "default_session"

# 默认检索模式（启动时设置）
DEFAULT_RETRIEVE_MODE = "smart"  # fast | smart | llm


# ============ SimpleAgent 类 ============
class SimpleAgent:
    """简单的 Agent，调用 MemU Service + LLM"""

    def __init__(self):
        self.llm = AsyncOpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )

    async def chat(self, user_input: str, session_id: str) -> str:
        """处理用户输入，返回回答"""

        # 1. 调用 MemU Service 检索记忆
        try:
            print("🔍 正在检索记忆...", end="", flush=True)
            retrieve_resp = requests.post(
                f"{MEMU_SERVICE_URL}/api/v1/retrieve",
                json={
                    "query": user_input,
                    "session_id": session_id,
                    "top_k": 5,
                },
                timeout=30,
            )
            retrieve_resp.raise_for_status()
            memories = retrieve_resp.json()
            print(" ✓")  # 显示完成标记
        except Exception as e:
            print(f" ✗")  # 显示失败标记
            print(f"⚠️  警告：检索记忆失败 - {e}")
            memories = {"items": [], "categories": []}

        # 2. 构建上下文
        context = self._build_context(user_input, memories)

        # 3. 调用 LLM 生成回答
        try:
            print("💬 正在生成回答...", end="", flush=True)
            response = await self.llm.chat.completions.create(
                model=DASHSCOPE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个有帮助的AI助手。请简洁地回答用户问题。",
                    },
                    {"role": "user", "content": context},
                ],
                temperature=0.7,
            )
            answer = response.choices[0].message.content
            print(" ✓")  # 显示完成标记
        except Exception as e:
            print(f" ✗")  # 显示失败标记
            return f"抱歉，生成回答时出错：{e}"

        # 4. 后台异步存储对话（不阻塞用户）
        asyncio.create_task(self._memorize_async(session_id, user_input, answer))

        return answer
    
    async def _memorize_async(self, session_id: str, input_text: str, output_text: str):
        """后台异步存储对话（不阻塞用户）"""
        try:
            # 使用 asyncio 的线程池执行同步的 HTTP 请求
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{MEMU_SERVICE_URL}/api/v1/memorize",
                    json={
                        "session_id": session_id,
                        "input_text": input_text,
                        "output_text": output_text,
                    },
                    timeout=30,
                )
            )
            # 静默成功，不显示任何提示
        except Exception:
            # 静默失败，不影响用户体验
            pass

    def _build_context(self, user_input: str, memories: dict) -> str:
        """构建对话上下文"""
        context = f"用户输入：{user_input}\n\n"

        if memories.get("items"):
            context += "相关记忆：\n"
            for item in memories["items"][:3]:
                summary = item.get("summary", item.get("content", ""))
                if summary:
                    context += f"- {summary}\n"
            context += "\n"

        context += "请根据以上信息回答用户问题。"
        return context


# ============ 主函数 ============
async def main():
    """主函数"""
    # 检查配置
    if DASHSCOPE_API_KEY == "your_dashscope_api_key_here":
        print("⚠️  警告：请先在 cli.py 中配置 DASHSCOPE_API_KEY")
        return

    # 检查 MemU Service 连接并触发初始化
    try:
        health_resp = requests.get(f"{MEMU_SERVICE_URL}/health", timeout=2)
        health_resp.raise_for_status()
        print("✅ MemU Service 连接正常")
        
        # 触发 MemoryService 初始化（通过一次空检索）
        try:
            init_resp = requests.post(
                f"{MEMU_SERVICE_URL}/api/v1/retrieve",
                json={"query": "__init__", "session_id": "__init__", "top_k": 1},
                timeout=10,
            )
            # 忽略结果，只是为了触发初始化
        except Exception:
            pass
    except Exception as e:
        print(f"❌ 无法连接到 MemU Service ({MEMU_SERVICE_URL})")
        print(f"   错误：{e}")
        print("   请先启动 MemU Service: uv run service.py\n")
        return

    # 设置检索模式（MemoryService 已初始化）
    try:
        print(f"⚙️  设置检索模式: {DEFAULT_RETRIEVE_MODE}...")
        mode_resp = requests.post(
            f"{MEMU_SERVICE_URL}/api/v1/config/retrieve-mode",
            json={"mode": DEFAULT_RETRIEVE_MODE},
            timeout=5
        )
        mode_resp.raise_for_status()
        mode_info = mode_resp.json()
        print(f"   ✓ {mode_info.get('description', 'OK')}\n")
    except Exception as e:
        print(f"⚠️  警告：设置检索模式失败 - {e}")
        print(f"   将使用服务当前配置\n")

    agent = SimpleAgent()
    
    # 创建 PromptSession 用于异步输入（不使用历史文件，避免触发 uvicorn reload）
    from prompt_toolkit import PromptSession
    session = PromptSession()

    print("\n🤖 MemU Agent CLI")
    print(f"   Service: {MEMU_SERVICE_URL}")
    print(f"   Session: {SESSION_ID}")
    print(f"   Retrieve Mode: {DEFAULT_RETRIEVE_MODE}")
    print("   Type 'exit' or 'quit' to stop.\n")

    # 交互循环
    while True:
        try:
            user_input = await session.prompt_async("You: ")
            user_input = user_input.strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break

        if user_input.lower() == "clear":
            print("\n" * 50)
            continue

        # 调用 agent
        answer = await agent.chat(user_input, SESSION_ID)
        print(f"\n{answer}\n")


if __name__ == "__main__":
    asyncio.run(main())
