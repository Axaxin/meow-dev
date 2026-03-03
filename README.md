# Meow Agent - MemU-Powered Interactive Agent

一个具有长期记忆能力的交互式 AI Agent，基于 [memU 框架](https://github.com/NevaMind-AI/memU)。

## 特性

- **基于 memU 框架** - 使用官方 memU SDK，支持智能记忆提取
- **混合检索策略** - memU SDK + PostgreSQL fallback，确保稳定检索
- **PostgreSQL + pgvector** - 持久化向量存储
- **智能记忆提取** - 自动提取 facts, preferences, skills
- **RAG 检索** - 毫秒级向量搜索
- **长期记忆** - 跨会话保持，重启不丢失
- **多模型支持** - 支持多种 LLM 和 Embedding 提供商

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

编辑 `.env` 文件：

```bash
# LLM 配置 (必需)
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=MiniMax-M2.5  # 或 qwen-turbo, gpt-4o-mini

# Embedding 配置 (必需)
# 选项 1: LMStudio (本地)
EMBEDDING_API_KEY=123
EMBEDDING_BASE_URL=http://127.0.0.1:1234/v1
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5

# 选项 2: OpenAI
# EMBEDDING_API_KEY=your_openai_key
# EMBEDDING_BASE_URL=https://api.openai.com/v1
# EMBEDDING_MODEL=text-embedding-3-small
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

# 添加到 .env
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/memu" >> .env
```

### 5. 运行

```bash
# 运行应用
uv run main.py

# 详细模式
uv run main.py --verbose

# 自定义 session
uv run main.py --session-id my_session
```

## 使用示例

```
🤖 MemU-Powered Agent Ready!
   Mode: local
   Session: default_session

You: 你好，我叫肥东
Agent: 你好肥东！很高兴认识你 😊

You: 我喜欢吃提拉米苏
Agent: 好的，我记住了！提拉米苏很美味

You: 我叫什么名字？
Agent: 你之前说你的名字是肥东 😊

You: 我喜欢吃什么？
Agent: 你说你喜欢吃提拉米苏

You: quit
Goodbye!
```

## CLI 参数

```bash
uv run main.py [OPTIONS]

Options:
  --mode, -m        存储模式: local (默认)
  --verbose, -v     启用详细输出
  --session-id, -s  会话 ID (默认: default_session)
  --proactive-interval  主动任务间隔 (秒, 默认: 60)
```

## 项目结构

```
.
├── src/meow_agent/
│   ├── config.py          # 配置管理
│   ├── models.py          # 数据模型
│   ├── event_bus.py       # 事件总线
│   ├── main.py            # CLI 入口
│   ├── memu/
│   │   └── client.py      # memU 客户端
│   └── agents/
│       ├── main_agent.py  # 主代理
│       └── memu_bot.py    # 记忆代理
├── tests/                 # 测试
│   ├── test_basic.py
│   ├── test_memu.py
│   └── test_postgres.py
├── scripts/               # 工具脚本
│   ├── quick_start_postgres.sh
│   └── setup_postgres_simple.sh
├── .env.example           # 环境配置示例
├── pyproject.toml         # 项目配置
└── README.md              # 本文件
```

## 开发

### 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行单个测试
uv run pytest tests/test_basic.py -v

# 运行 memU 测试
uv run python tests/test_memu.py

# 运行 PostgreSQL 测试
uv run python tests/test_postgres.py
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

## 架构

### 三层记忆架构

```
Resource (原始数据)
    ↓
Memory Item (提取的事实、偏好、技能)
    ↓
Category (主题分类)
    ↓
PostgreSQL (持久化存储)
```

### 组件

- **MainAgent**: 用户交互，检索记忆，生成响应
- **MemUBot**: 后台记忆提取，意图预测，主动建议
- **EventBus**: 异步事件通信
- **MemUClient**: memU SDK 封装，实现混合检索策略
  - 优先使用 memU SDK retrieve()
  - 如果返回空结果，fallback 到 PostgreSQL 直接查询
  - 确保 100% 检索成功率

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

### 问题：记忆不工作

```bash
# 1. 检查 PostgreSQL 状态
docker ps | grep memu-postgres

# 2. 检查 pgvector 扩展
docker exec memu-postgres psql -U postgres -d memu -c "SELECT * FROM pg_extension WHERE extname='vector';"

# 3. 用 verbose 模式运行查看详细日志
uv run main.py --verbose

# 4. 检查数据库中是否有数据
docker exec memu-postgres psql -U postgres -d memu -c "SELECT COUNT(*) FROM memory_items;"
```

**注意**: 系统使用混合检索策略（memU SDK + PostgreSQL fallback），即使 SDK 返回空结果，也会通过直接数据库查询检索记忆。

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
- **Embedding 生成**: <1秒 (本地)
- **混合检索**: SDK 优先，数据库 fallback 确保稳定性

## 文档

- [CHANGELOG.md](CHANGELOG.md) - 版本更新记录
- [DESIGN.md](DESIGN.md) - 架构设计
- [AGENTS.md](AGENTS.md) - 开发指南

## 技术栈

- **memU SDK** - 记忆框架
- **PostgreSQL + pgvector** - 向量数据库
- **SQLAlchemy** - ORM
- **Pydantic** - 数据验证
- **OpenAI Python SDK** - LLM 客户端

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
