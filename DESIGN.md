# MemU Service + CLI Client - 设计文档

**当前版本**: v1.1.0

## 1. 架构概述

本项目基于 [memU 框架](https://github.com/NevaMind-AI/memU) 构建，采用服务 + 客户端分离架构。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MemU Service (FastAPI)                               │
│                              端口 8000                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  API 层                                                                       │
│  ├── POST /api/v1/memorize                                                  │
│  ├── POST /api/v1/retrieve                                                  │
│  ├── GET  /api/v1/config                                                    │
│  ├── POST /api/v1/config/retrieve-mode                                      │
│  └── GET  /health                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  业务层                                                                       │
│  ├── MemUServiceClient (包装 memU SDK)                                      │
│  ├── 动态配置管理 (fast/smart/llm 模式)                                      │
│  └── 智能缓存 (5分钟 TTL)                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  数据层                                                                       │
│  ├── memU SDK (官方)                                                        │
│  └── PostgreSQL + pgvector                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
         ↑ HTTP RESTful API
         │
┌────────┴─────────────────────────────────────────────────────────────────────┐
│                          CLI 客户端 (cli.py)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  用户交互层                                                                   │
│  ├── 用户输入/输出循环                                                       │
│  ├── 进度提示 (🔍 💬 ✓)                                                      │
│  └── 异步后台存储 (不阻塞用户)                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  SimpleAgent                                                                 │
│  ├── 调用 LLM 生成回答                                                       │
│  ├── 调用 MemU Service API                                                  │
│  └── 自动设置检索模式 (默认 smart)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 实际项目结构

```
src/meow_agent/
├── core/                       # 共享核心
│   ├── __init__.py
│   ├── config.py              # 配置管理 (pydantic-settings)
│   └── models.py              # 数据模型 (dataclasses)
├── service/                   # MemU Service
│   ├── __init__.py            # FastAPI app
│   ├── main.py                # 启动入口
│   ├── dependencies.py        # 依赖注入 + 动态配置
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── memory.py          # 记忆 API
│   │   ├── config.py          # 配置 API
│   │   └── health.py          # 健康检查
│   └── models/
│       ├── __init__.py
│       └── schemas.py         # Pydantic 模型

cli.py                        # CLI 客户端 (单文件)
service.py                   # Service 启动脚本
```

## 3. 核心组件

### 3.1 MemUClient (`memu/client.py`)

封装 memU 官方 SDK：

```python
from memu.app import MemoryService

class MemUClient:
    def __init__(self, use_cloud: bool = False):
        """初始化 MemU 客户端"""
        # 使用官方 MemoryService
        self.service = MemoryService(
            llm_profiles={
                "default": {
                    "api_key": settings.dashscope_api_key,
                    "base_url": settings.dashscope_base_url,
                    "chat_model": settings.dashscope_model,
                },
                "embedding": {
                    "api_key": settings.embedding_api_key,
                    "base_url": settings.embedding_base_url,
                    "embed_model": settings.embedding_model,
                } if settings.embedding_base_url else None,
            },
            database_config={
                "metadata_store": {"provider": "inmemory"},  # 本地模式
            },
            memorize_config={
                "memory_types": ["fact", "preference", "skill", "intent", "todo"],
                "memory_categories": self._get_default_categories(),
            },
            retrieve_config={"method": "rag"},
        )
    
    async def memorize_interaction(
        self, session_id: str, input_text: str, output_text: str
    ) -> str:
        """存储对话并提取记忆项"""
        # 准备对话数据
        conversation_data = {
            "messages": [
                {"role": "user", "content": input_text},
                {"role": "assistant", "content": output_text},
            ]
        }
        
        # 保存为临时文件
        temp_file = f"/tmp/conversation_{session_id}.json"
        with open(temp_file, "w") as f:
            json.dump(conversation_data, f)
        
        # 使用 memU memorize
        result = await self.service.memorize(
            resource_url=temp_file,
            modality="conversation",
            user={"user_id": session_id},
        )
        
        return result.get("resource", {}).get("id", "")
    
    async def retrieve(
        self, query: str, session_id: str, mode: str = "hybrid", top_k: int = 5
    ) -> RetrievedContext:
        """检索相关记忆"""
        # 构建查询
        queries = [{"role": "user", "content": {"text": query}}]
        
        # 使用 memU retrieve
        result = await self.service.retrieve(
            queries=queries,
            where={"user_id": session_id},
            method=mode if mode != "hybrid" else "rag",
        )
        
        return RetrievedContext(
            items=result.get("items", []),
            categories=result.get("categories", []),
            llm_context=result.get("llm_context", ""),
        )
```

### 3.2 MainAgent (`agents/main_agent.py`)

用户交互代理（保持不变）：

```python
class MainAgent:
    async def handle(user_query: str, session_id: str) -> Response:
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

### 3.3 MemoryService (官方 SDK)

memU 官方提供的核心服务：

```python
from memu.app import MemoryService

# 初始化
service = MemoryService(
    llm_profiles={
        "default": {
            "api_key": "your_api_key",
            "chat_model": "gpt-4o-mini",
        }
    }
)

# 记忆
result = await service.memorize(
    resource_url="path/to/file.json",
    modality="conversation",  # conversation, document, image, video, audio
    user={"user_id": "123"}
)

# 检索 (RAG 模式)
result_rag = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "query"}}],
    where={"user_id": "123"},
    method="rag"
)

# 检索 (LLM 模式 - 深度推理)
result_llm = await service.retrieve(
    queries=[{"role": "user", "content": {"text": "query"}}],
    where={"user_id": "123"},
    method="llm"
)
```

## 4. 数据模型

### 4.1 Memory Item (memU 格式)

```python
{
    "id": "item_xxx",
    "memory_type": "fact",  # fact/preference/skill/intent/todo
    "summary": "用户的名字是小明",
    "content": "详细内容...",
    "confidence": 0.95,
    "tags": ["name", "profile"],
    "embedding": [0.1, 0.2, ...],  # 1024维向量
    "access_count": 5,
    "created_at": "2026-03-03T10:00:00Z",
}
```

### 4.2 Category (memU 格式)

```python
{
    "id": "cat_xxx",
    "name": "user_profile",
    "description": "用户个人信息和偏好",
    "summary": "用户小明，喜欢Python编程...",
    "item_ids": ["item_001", "item_002"],
    "access_frequency": "high",
}
```

### 4.3 Memory File System

记忆以 Markdown 文件形式组织：

```markdown
# preferences/communication_style.md

## Summary
用户偏好简洁、友好的沟通风格。

## Details
- 喜欢直接了当的回答
- 偏好中文交流
- 对技术问题需要详细解释

## Related Items
- item_001: 偏好简洁沟通
- item_002: 喜欢中文交流

## Access Stats
- Access count: 15
- Last accessed: 2026-03-03
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
│   ├── 保存对话为 JSON 文件                                   │
│   └── service.memorize() → memU SDK 处理:                   │
│       ├── 提取 memory items (LLM)                           │
│           ├── fact: "用户的名字是小明"                       │
│           └── preference: "用户喜欢Python"                  │
│       ├── 生成 embeddings                                   │
│       ├── 自动分类到 categories                             │
│       └── 生成 Markdown 文件                                │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
生成文件:
memory/
├── user_profile/
│   └── basic_info.md  # 包含"用户名字是小明"
└── programming/
    └── interests.md    # 包含"用户喜欢Python"
    │
    ▼
用户下次问: "我叫什么名字？"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ service.retrieve() → RAG 搜索找到相关记忆                   │
│   ├── Query embedding 匹配                                  │
│   ├── 找到 user_profile/basic_info.md                       │
│   └── 返回 "用户的名字是小明"                                │
│                                                              │
│ _build_context() → 注入记忆到上下文                          │
│ _generate_response() → "你之前说你的名字是小明"              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 配置

```bash
# .env
# LLM 配置
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=kimi-k2.5

# Embedding 配置 (可选，不配置则使用 memU 默认)
EMBEDDING_API_KEY=your_embedding_key
EMBEDDING_BASE_URL=http://127.0.0.1:1234/v1
EMBEDDING_MODEL=text-embedding-qwen3-embedding-0.6b

# Memory 配置
MEMORY_STORE_PATH=./memory
MODE=local  # local 或 cloud
VERBOSE=false

# Agent 配置
PROACTIVE_INTERVAL=60  # 主动记忆间隔(秒)
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

## 8. 关键特性

### 8.1 三层记忆架构

| Layer | 说明 | memU 实现 |
|-------|------|-----------|
| **Resource** | 原始数据 | JSON/文件输入 |
| **Memory Item** | 提取的事实、偏好、技能 | 自动提取 + embedding |
| **Category** | 主题分类 | 自动分类 + Markdown 文件 |

### 8.2 双模式检索

| 模式 | 速度 | 成本 | 适用场景 |
|------|------|------|----------|
| **RAG** | ⚡ 毫秒级 | 💰 仅 embedding | 实时建议、快速检索 |
| **LLM** | 🐢 秒级 | 💰💰 LLM 推理 | 复杂推理、意图预测 |

### 8.3 主动记忆 (Proactive Memory)

- 24/7 后台监控用户交互
- 自动提取和分类记忆
- 热点话题追踪
- 主动建议和提醒

## 9. 与旧版本的区别

| 特性 | 旧版本 (自定义实现) | 新版本 (memU 框架) |
|------|---------------------|-------------------|
| **存储格式** | JSON 文件 | Markdown 文件系统 |
| **目录结构** | 扁平化 | 分层分类 |
| **可读性** | 需要解析 JSON | 可直接阅读 MD |
| **分类** | 手动 | 自动智能分类 |
| **检索** | 简单向量搜索 | RAG + LLM 双模式 |
| **主动记忆** | 基础实现 | 完整的 24/7 支持 |
| **维护** | 需要自己维护 | 官方维护更新 |

## 10. 演进路线

| Phase | 状态 | 说明 |
|-------|------|------|
| Phase 1 (重构) | 🚧 进行中 | 迁移到 memU 官方框架 |
| Phase 2 | 🔜 计划中 | 多模态支持 (图像、音频) |
| Phase 3 | 🔜 计划中 | Cloud API 集成 |
| Phase 4 | 🔜 计划中 | 群体记忆 (跨用户知识共享) |
| Phase 5 | 🔜 计划中 | 自我进化 (自动重组、热点检测) |
