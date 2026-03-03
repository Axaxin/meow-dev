# MemU-Powered Interactive Agent - 设计文档

## 1. 架构概述

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE (CLI)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           ▼                           ▼                           ▼
┌─────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────┐
│   🤖 MAIN AGENT     │  │    🔄 EVENT BUS         │  │    🧠 MEMU BOT      │
│  (User-Facing)      │◄─┤   (Async Pub/Sub)       │─┤│  (Background)       │
├─────────────────────┤  └─────────────────────────┘  ├─────────────────────┤
│ • Receive query     │                               │ • Monitor events    │
│ • Retrieve memories │                               │ • Intent prediction │
│ • Build context     │                               │ • Proactive tasks   │
│ • Generate response │                               │                     │
│ • Store interaction │                               │                     │
└─────────────────────┘                               └─────────────────────┘
                                       │                           │
                                       └───────────┬───────────────┘
                                                   ▼
                                       ┌─────────────────────┐
                                       │   💾 MEMU CLIENT    │
                                       │  (3-Layer Memory)   │
                                       ├─────────────────────┤
                                       │  Resource Layer     │
                                       │  Memory Item Layer  │
                                       │  Category Layer     │
                                       └─────────────────────┘
                                                   │
                                                   ▼
                                       ┌─────────────────────┐
                                       │  📁 LOCAL STORE     │
                                       │  (JSON Files)       │
                                       └─────────────────────┘
```

## 2. 实际项目结构

```
src/meow_agent/
├── __init__.py           # 包初始化
├── config.py             # 配置管理 (pydantic-settings)
├── models.py             # 数据模型 (dataclasses)
├── event_bus.py          # 异步事件总线
├── main.py               # CLI 入口点
├── memu/
│   ├── __init__.py
│   ├── client.py         # MemU 客户端 (核心记忆逻辑)
│   └── local_store.py    # JSON 文件存储实现
└── agents/
    ├── __init__.py
    ├── main_agent.py     # 主代理 (用户交互)
    └── memu_bot.py       # 记忆代理 (后台处理)

memory_store/             # 记忆存储目录
├── resources.json        # 原始对话数据
├── items.json            # 提取的记忆项
└── categories.json       # 分类组织

tests/
└── test_basic.py         # 单元测试
```

## 3. 核心组件

### 3.1 MemUClient (`memu/client.py`)

核心记忆客户端，实现三层记忆架构：

```python
class MemUClient:
    async def memorize_interaction(session_id, input_text, output_text) -> str:
        """存储对话并提取记忆项"""
        # 1. 创建 Resource (原始对话)
        # 2. 使用 LLM 提取 Memory Items
        # 3. 生成 embedding 用于检索

    async def retrieve(query, session_id, mode, top_k) -> RetrievedContext:
        """检索相关记忆"""
        # 1. 生成 query embedding
        # 2. 向量相似度搜索
        # 3. 更新 access_count

    async def _extract_memory_items(...) -> list[dict]:
        """使用 LLM 从对话中提取记忆项"""
        # 调用 DashScope API 提取: fact/preference/skill/intent/todo
```

### 3.2 MainAgent (`agents/main_agent.py`)

用户交互代理：

```python
class MainAgent:
    async def handle(user_query, session_id) -> Response:
        # 1. 检索相关记忆
        memories = await self.memu.retrieve(query, session_id)
        # 2. 构建增强上下文
        context = self._build_context(query, memories)
        # 3. 调用 LLM 生成响应
        response = await self._generate_response(context)
        # 4. 异步存储对话
        asyncio.create_task(self.memu.memorize_interaction(...))
        return response
```

### 3.3 LocalMemoryStore (`memu/local_store.py`)

JSON 文件存储实现：

```python
class LocalMemoryStore:
    # Resource Layer
    def create_resource(data) -> dict
    def get_resource(id) -> dict | None

    # Memory Item Layer
    def create_memory_item(data) -> dict
    def search_items(query_embedding, top_k) -> list[dict]
    def update_memory_item_access(id) -> None

    # Category Layer
    def create_category(data) -> dict
    def add_item_to_category(category_id, item_id) -> bool
```

## 4. 数据模型

### 4.1 MemoryItem (Layer 2)

```python
@dataclass
class MemoryItem:
    id: str
    resource_id: str
    type: MemoryItemType  # fact/preference/skill/intent/todo
    content: str
    embedding: list[float]  # 64维向量
    confidence: float  # 0-1
    tags: list[str]
    access_count: int = 0
    last_accessed: str | None = None
    created_at: str
```

### 4.2 Resource (Layer 1)

```python
@dataclass
class Resource:
    id: str
    type: str  # "conversation"
    content: dict[str, Any]  # {"input": ..., "output": ...}
    session_id: str
    timestamp: str
    metadata: dict[str, Any]
```

## 5. 记忆流程

```
用户输入: "你好，我是小明，我喜欢Python"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ MainAgent.handle()                                          │
│   ├── retrieve() → 检索相关记忆 (首次为空)                   │
│   ├── _build_context() → 构建上下文                          │
│   ├── _generate_response() → LLM 生成响应                    │
│   └── memorize_interaction() [async] → 存储记忆              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ MemUClient.memorize_interaction()                           │
│   ├── create_resource() → 存储 raw conversation             │
│   ├── _extract_memory_items() → LLM 提取:                   │
│   │       ├── fact: "用户的名字是小明"                       │
│   │       └── preference: "用户喜欢Python"                  │
│   └── create_memory_item() → 存储带 embedding 的记忆项      │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
用户下次问: "我叫什么名字？"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ retrieve() → 向量搜索找到 "用户的名字是小明"                 │
│ _build_context() → 注入记忆到上下文                          │
│ _generate_response() → "你之前说你的名字是小明"              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 配置

```bash
# .env
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=kimi-k2.5

MEMORY_STORE_PATH=./memory_store
MODE=local
VERBOSE=false
```

## 7. 运行

```bash
# 安装依赖
uv sync

# 运行 Agent
uv run main.py --mode local

# 带详细输出
uv run main.py --mode local --verbose

# 运行测试
uv run pytest tests/ -v
```

## 8. 演进路线

| Phase | 状态 | 说明 |
|-------|------|------|
| Phase 1 (MVP) | ✅ 已完成 | 基础记忆 + 本地 JSON 存储 |
| Phase 2 | 🔜 计划中 | MemU Cloud API 集成 |
| Phase 3 | 🔜 计划中 | 多模态支持 (图像、音频) |
| Phase 4 | 🔜 计划中 | 自我进化 (热点检测、自动重组) |
| Phase 5 | 🔜 计划中 | 群体记忆 (跨用户知识共享) |
