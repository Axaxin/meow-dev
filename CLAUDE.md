# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MemU-Powered Interactive Agent - 一个结合 MemU 记忆框架的交互式 AI Agent，支持三层记忆架构和长期记忆能力。

- **Python Version**: 3.13+
- **Package Manager**: uv
- **LLM Backend**: DashScope (OpenAI 兼容端点)
- **Memory Storage**: 本地 JSON 文件存储

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   MAIN AGENT    │  │   EVENT BUS     │  │    MEMU BOT     │
│  (User-Facing)  │◄─┤   (Pub/Sub)     │─┤│  (Background)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                                       │
          └───────────────┬───────────────────────┘
                          ▼
              ┌─────────────────────┐
              │    MEMU CLIENT      │
              │  (3-Layer Memory)   │
              ├─────────────────────┤
              │  Resource Layer     │
              │  Memory Item Layer  │
              │  Category Layer     │
              └─────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  LOCAL JSON STORE   │
              │  ./memory_store/    │
              └─────────────────────┘
```

## Project Structure

```
src/meow_agent/
├── __init__.py           # 包初始化
├── config.py             # 配置管理 (pydantic-settings)
├── models.py             # 数据模型
├── event_bus.py          # 异步事件总线
├── main.py               # CLI 入口
├── memu/
│   ├── __init__.py
│   ├── client.py         # MemU 客户端 (记忆核心)
│   └── local_store.py    # JSON 文件存储
└── agents/
    ├── __init__.py
    ├── main_agent.py     # 主代理 (用户交互)
    └── memu_bot.py       # 记忆代理 (后台处理)

memory_store/             # 记忆存储目录
├── resources.json        # 原始对话数据
├── items.json            # 提取的记忆项
└── categories.json       # 分类组织

tests/                    # 测试文件
└── test_basic.py
```

## Common Commands

```bash
# 运行 Agent (本地模式)
uv run main.py --mode local

# 带详细输出
uv run main.py --mode local --verbose

# 指定 session ID
uv run main.py --session-id my_session

# 运行测试
uv run pytest tests/ -v

# 添加依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>
```

## Key Components

### 1. MemUClient (`memu/client.py`)
核心记忆客户端，提供：
- `memorize_interaction()` - 存储对话并提取记忆项
- `retrieve()` - 检索相关记忆 (向量相似度搜索)
- `get_hot_topics()` - 获取热点话题

### 2. MainAgent (`agents/main_agent.py`)
用户交互代理：
- 接收用户查询
- 检索相关记忆增强上下文
- 调用 LLM 生成响应
- 异步存储对话记忆

### 3. LocalMemoryStore (`memu/local_store.py`)
JSON 文件存储实现：
- 资源层 CRUD
- 记忆项 CRUD + 向量搜索
- 分类层管理

### 4. EventBus (`event_bus.py`)
异步发布/订阅事件总线，支持：
- `user_input` - 用户输入事件
- `agent_output` - 代理输出事件
- `proactive_suggestion` - 主动建议事件
- `tick` - 定时触发事件

## Configuration

环境变量配置 (`.env`):

```bash
# LLM 配置 (DashScope)
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=kimi-k2.5

# Embedding 配置 (可选)
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=

# 记忆存储路径
MEMORY_STORE_PATH=./memory_store

# 运行配置
MODE=local
VERBOSE=false
PROACTIVE_INTERVAL=60
```

## Memory Flow

1. **用户输入** → MainAgent 接收查询
2. **记忆检索** → MemUClient 检索相关记忆
3. **上下文构建** → 合并查询 + 记忆上下文
4. **LLM 响应** → 生成回答
5. **记忆存储** → 异步提取并存储记忆项

## Data Models

- `Resource` - 原始对话数据 (Layer 1)
- `MemoryItem` - 细粒度记忆项 (Layer 2)，包含：
  - type: fact/preference/skill/intent/todo
  - content: 记忆内容
  - embedding: 向量嵌入
  - confidence: 置信度
  - tags: 标签
- `Category` - 主题分类 (Layer 3)

## Testing

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_basic.py::TestLocalMemoryStore -v
```

## Notes

- 记忆存储使用异步任务，程序退出前会等待存储完成
- Embedding 默认使用 hash-based fallback，可配置外部 API
- 支持跨 session 的记忆检索 (使用相同 session_id)
