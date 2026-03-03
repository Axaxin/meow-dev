# Meow Agent - MemU Service + CLI 客户端

基于 [memU 框架](https://github.com/NevaMind-AI/memU) 的记忆存储服务 + 独立 CLI 客户端。

**当前版本**: v1.1.0

## ✨ 新功能 (v1.1.0)

- 🎛️ **动态配置 API**: 支持运行时切换检索模式（fast/smart/llm）
- ⚡ **性能优化**: CLI 异步后台存储，响应时间从 ~18s 降至 ~3s
- 🚀 **CLI 自动配置**: 启动时自动设置检索模式（默认 smart）
- 💾 **智能缓存**: 5分钟内存缓存，重复查询仅需 0.02s

## 架构

```
┌──────────────────────────────────────┐
│  MemU Service (FastAPI)              │  端口 8000
│  独立的记忆存储/检索服务               │
│  ├─ POST /api/v1/memorize            │
│  ├─ POST /api/v1/retrieve            │
│  ├─ GET  /api/v1/memories            │
│  └─ GET  /health                     │
├──────────────────────────────────────┤
│  memU SDK                            │
├──────────────────────────────────────┤
│  PostgreSQL + pgvector               │
└──────────────────────────────────────┘
         ↑ HTTP RESTful API
         │
┌────────┴─────────────────────────────┐
│  CLI 客户端 (cli.py)                  │
│  ├─ 用户交互                          │
│  ├─ SimpleAgent (对话处理)            │
│  └─ LLM 调用 + MemU Service API      │
└──────────────────────────────────────┘
```

## 特性

- **独立服务架构** - MemU Service 作为独立 FastAPI 服务
- **单文件 CLI** - cli.py 完全独立，只需 requests + prompt_toolkit
- **memU SDK 集成** - 直接调用 memU SDK，无需额外包装
- **PostgreSQL + pgvector** - 持久化向量存储
- **智能记忆提取** - 自动提取 facts, preferences, skills
- **RAG 检索** - 毫秒级向量搜索
- **长期记忆** - 跨会话保持，重启不丢失

## 快速开始

### 1. 环境要求

- Python 3.13+
- Docker (用于 PostgreSQL)
- [uv](https://github.com/astral-sh/uv) 包管理器

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/meow-agent.git
cd meow-agent

# 安装依赖
uv sync

# 复制环境配置
cp .env.example .env
```

### 3. 配置

编辑 `.env` 文件（MemU Service 配置）：

```bash
# Database (必需)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/memu

# LLM (for memU SDK)
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=gpt-4o-mini

# Embedding (for memU SDK)
EMBEDDING_API_KEY=your_embedding_key
EMBEDDING_BASE_URL=http://127.0.0.1:1234/v1
EMBEDDING_MODEL=text-embedding-3-small
```

编辑 `cli.py` 文件（CLI 客户端配置）：

```python
MEMU_SERVICE_URL = "http://localhost:8000"
DASHSCOPE_API_KEY = "your_api_key_here"  # 替换为你的 API key
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/v1"
DASHSCOPE_MODEL = "gpt-4o-mini"
SESSION_ID = "default_session"
```

### 4. 启动 PostgreSQL

```bash
# 使用脚本自动部署
./scripts/quick_start_postgres.sh

# 或手动部署
docker run -d \
  --name memu-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=memu \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 启用 pgvector 扩展
docker exec -i memu-postgres psql -U postgres -d memu << 'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
SQL
```

### 5. 启动服务

**终端 1：启动 MemU Service**

```bash
# 方式 1：使用脚本入口（推荐）
uv run service.py

# 方式 2：直接使用 uvicorn
uv run uvicorn src.meow_agent.service:app --host 0.0.0.0 --port 8000 --reload

# 方式 3：使用已安装的命令
uv run memu-service
```

**终端 2：启动 CLI 客户端**

```bash
# CLI 会自动设置检索模式为 smart（可在 cli.py 中修改 DEFAULT_RETRIEVE_MODE）
uv run cli.py

# 或使用已安装的命令
uv run memu-cli
```

**访问 API 文档**

```bash
# Swagger UI
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc
```

## 使用示例

### CLI 客户端

```
🤖 MemU Agent CLI
   Service: http://localhost:8000
   Session: default_session
   Type 'exit' or 'quit' to stop.

You: 你好
Agent: 你好！有什么可以帮助你的吗？

You: 我喜欢简洁的回答
Agent: 好的，我会尽量简洁地回答你的问题。

You: 我的偏好是什么？
Agent: 根据记忆，你喜欢简洁的回答。

You: exit
Goodbye!
```

### API 调用

```bash
# 健康检查
curl http://localhost:8000/health

# 存储记忆
curl -X POST http://localhost:8000/api/v1/memorize \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","input_text":"你好","output_text":"你好！"}'

# 检索记忆
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"用户说了什么","session_id":"test"}'
```

## API 文档

MemU Service 提供以下 RESTful API：

### 🎛️ 配置管理

#### GET /api/v1/config
查看当前配置

**响应：**
```json
{
  "retrieve_mode": "fast",
  "cache_size": 5,
  "verbose": true
}
```

#### POST /api/v1/config/retrieve-mode
动态设置检索模式

**请求：**
```json
{
  "mode": "fast"  // fast | smart | llm
}
```

**模式说明：**
- **fast**（推荐）：纯向量搜索，~0.2-1s
- **smart**：向量搜索 + LLM 判断，~5-10s
- **llm**：完全 LLM 检索，~10-15s

**响应：**
```json
{
  "mode": "smart",
  "description": "Smart mode: Vector search with LLM judgment (~5-10s)",
  "config": {
    "method": "rag",
    "route_intention": true,
    "sufficiency_check": true
  }
}
```

**使用示例：**
```bash
# 切换到智能模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"smart"}'

# 切换回快速模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"fast"}'
```

### 📝 记忆操作

#### POST /api/v1/memorize
存储对话到记忆系统

**请求：**
```json
{
  "session_id": "user_001",
  "input_text": "你好",
  "output_text": "你好！有什么可以帮助你的吗？",
  "metadata": {}  // 可选
}
```

**响应：**
```json
{
  "resource_id": "res_000001",
  "items_extracted": 3,
  "success": true
}
```

### POST /api/v1/retrieve
检索相关记忆（使用当前配置的模式）

**请求：**
```json
{
  "query": "用户偏好",
  "session_id": "user_001",
  "top_k": 5
}
```

**注意**：检索模式通过 `/api/v1/config/retrieve-mode` 动态设置，默认为 "fast" 模式。

**响应：**
```json
{
  "items": [
    {
      "id": "item_001",
      "memory_type": "preference",
      "summary": "用户喜欢简洁的回答",
      "confidence": 0.9
    }
  ],
  "categories": [],
  "llm_context": ""
}
```

### GET /api/v1/memories
列出记忆（暂未实现）

### GET /health
健康检查

## 项目结构

```
.
├── src/meow_agent/
│   ├── core/                  # 共享核心
│   │   ├── config.py          # 配置管理
│   │   └── models.py          # 数据模型
│   └── service/               # MemU Service
│       ├── __init__.py        # FastAPI app
│       ├── main.py            # 启动入口
│       ├── dependencies.py    # 依赖注入
│       ├── routes/
│       │   ├── memory.py      # 记忆 API
│       │   └── health.py      # 健康检查
│       └── models/
│           └── schemas.py     # Pydantic 模型
├── cli.py                     # CLI 客户端（单文件）
├── service.py                 # Service 启动脚本
├── tests/                     # 测试
│   ├── test_basic.py
│   └── test_postgres.py
├── scripts/                   # 工具脚本
│   ├── quick_start_postgres.sh
│   └── setup_postgres_simple.sh
├── .env.example               # 环境配置示例
├── pyproject.toml             # 项目配置
└── README.md                  # 本文件
```

## 开发

### 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行单个测试
uv run pytest tests/test_basic.py -v
```

### 添加依赖

```bash
uv add <package>
uv add --dev <package>
```

## 配置说明

### LLM 模型

支持任何 OpenAI 兼容的端点：

| 提供商 | BASE_URL | 模型示例 |
|--------|----------|----------|
| DashScope | https://dashscope.aliyuncs.com/v1 | MiniMax-M2.5, qwen-turbo |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini, gpt-3.5-turbo |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| 本地 (LMStudio/Ollama) | http://127.0.0.1:1234/v1 | 任何模型 |

### Embedding 模型

**推荐配置**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| **LMStudio (本地)** | 免费、快速、隐私 | 需要本地部署 |
| **OpenAI** | 最稳定、高质量 | 付费 |
| **DashScope** | 国内友好 | 付费 |

## 数据库管理

### PostgreSQL 命令

```bash
# 启动
docker start memu-postgres

# 停止
docker stop memu-postgres

# 查看日志
docker logs memu-postgres

# 连接数据库
docker exec -it memu-postgres psql -U postgres -d memu

# 查看记忆
SELECT COUNT(*) FROM memory_items;
SELECT memory_type, content FROM memory_items LIMIT 5;

# 备份
docker exec memu-postgres pg_dump -U postgres memu > backup.sql

# 恢复
cat backup.sql | docker exec -i memu-postgres psql -U postgres memu
```

## 架构说明

### 三层记忆架构（memU SDK 内部）

```
Resource (原始数据)
    ↓
Memory Item (提取的事实、偏好、技能)
    ↓
Category (主题分类)
    ↓
PostgreSQL (持久化存储)
```

### 组件说明

- **MemU Service**: FastAPI 服务，提供 RESTful API
- **memU SDK**: 官方 SDK，处理记忆提取和检索
- **SimpleAgent**: CLI 客户端中的 Agent，调用 MemU Service + LLM

## 故障排除

### 问题：Docker 镜像下载慢

```bash
# 配置 Docker 镜像源
# 编辑 ~/.docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn"
  ]
}

# 重启 Docker Desktop
```

### 问题：MemU Service 无法启动

```bash
# 1. 检查 PostgreSQL 状态
docker ps | grep memu-postgres

# 2. 检查 pgvector 扩展
docker exec memu-postgres psql -U postgres -d memu -c "SELECT * FROM pg_extension WHERE extname='vector';"

# 3. 检查配置
cat .env | grep DATABASE_URL
cat .env | grep DASHSCOPE_API_KEY

# 4. 用 verbose 模式运行查看详细日志
VERBOSE=true uv run service.py
```

### 问题：CLI 客户端无法连接 Service

```bash
# 1. 检查 Service 是否运行
curl http://localhost:8000/health

# 2. 检查配置
# 编辑 cli.py，确认 MEMU_SERVICE_URL 和 DASHSCOPE_API_KEY

# 3. 检查端口占用
lsof -i :8000
```

### 问题：Embedding 404 错误

确保 Embedding 服务正常运行：

```bash
# 测试 LMStudio embedding
curl http://127.0.0.1:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "model": "text-embedding-nomic-embed-text-v1.5"}'
```

## 性能

- **记忆提取**: ~15秒 (取决于 LLM 速度)
- **RAG 检索**: <100ms (PostgreSQL 向量搜索)
- **API 响应**: <50ms (FastAPI)
- **CLI 交互**: <1秒 (本地 LLM)

## 文档

- [CHANGELOG.md](CHANGELOG.md) - 版本更新记录
- [AGENTS.md](AGENTS.md) - 开发指南

## 技术栈

- **FastAPI** - Web 框架
- **memU SDK** - 记忆框架
- **PostgreSQL + pgvector** - 向量数据库
- **Pydantic** - 数据验证
- **OpenAI Python SDK** - LLM 客户端
- **prompt-toolkit** - CLI 交互

## License

MIT

## 相关链接

- [memU 框架](https://github.com/NevaMind-AI/memU)
- [memU 文档](https://memu.pro/docs)
- [memU Cloud](https://memu.so)


## 贡献

欢迎提交 Issue 和 Pull Request！

## 致谢

感谢 [memU](https://github.com/NevaMind-AI/memU) 团队提供的优秀框架！

## 🎯 推荐配置

### 默认配置（适合 90% 场景）
- **模式**：fast（快速模式）
- **响应时间**：0.2-1 秒
- **适用场景**：日常对话、快速响应

### 智能配置（需要时切换）
- **模式**：smart（智能模式）
- **响应时间**：5-10 秒
- **适用场景**：复杂查询、需要智能判断

### 使用建议

1. **默认使用 fast 模式**：快速响应，用户体验好
2. **需要时切换到 smart 模式**：复杂查询或需要更准确的结果
3. **利用缓存**：相同查询会从缓存读取（0.02 秒）

### 性能对比

| 操作 | Fast 模式 | Smart 模式 | 缓存命中 |
|------|----------|-----------|---------|
| **检索** | 0.2-1s | 5-10s | 0.02s |
| **存储** | ~15s | ~15s | - |
| **用户体验** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 🔧 故障排除

### 问题：检索速度慢

**检查当前模式：**
```bash
curl http://localhost:8000/api/v1/config
```

**解决方案：**
```bash
# 切换到快速模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"fast"}'
```

### 问题：检索结果不准确

**解决方案：**
```bash
# 切换到智能模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"smart"}'
```

### 问题：缓存占用过多内存

**解决方案：**
```bash
# 清除缓存
curl -X POST http://localhost:8000/api/v1/config/clear-cache
```
