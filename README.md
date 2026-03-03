# Meow Agent - MemU-Powered Interactive Agent

一个具有长期记忆能力的交互式 AI Agent，基于 MemU 三层记忆架构。

## 特性

- **三层记忆架构** - Resource → Memory Item → Category
- **智能记忆提取** - 使用 LLM 自动从对话中提取关键信息
- **语义检索** - 基于向量相似度的记忆搜索
- **长期记忆** - 跨会话保持和检索记忆
- **本地存储** - JSON 文件存储，无需数据库

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=kimi-k2.5
```

### 3. 运行

```bash
uv run main.py
```

## 使用示例

```
🤖 MemU-Powered Agent Ready!
   Mode: local
   Session: default_session
   Type 'exit' or 'quit' to stop.

You: 你好，我是小明，我喜欢学习Python

Agent: 你好小明！很高兴认识你 👋
       Python是非常棒的编程语言...

You: 我之前说我叫什么名字？

Agent: 你之前说你的名字是小明 😊

You: 我喜欢什么？

Agent: 你说你喜欢学习Python
```

## CLI 参数

```bash
uv run main.py [OPTIONS]

Options:
  --mode, -m        存储模式: local (默认) 或 cloud
  --verbose, -v     启用详细输出
  --session-id, -s  会话 ID (默认: default_session)
  --proactive-interval  主动任务间隔 (秒, 默认: 60)
```

## 项目结构

```
src/meow_agent/
├── config.py          # 配置管理
├── models.py          # 数据模型
├── event_bus.py       # 事件总线
├── main.py            # CLI 入口
├── memu/
│   ├── client.py      # MemU 客户端
│   └── local_store.py # 本地存储
└── agents/
    ├── main_agent.py  # 主代理
    └── memu_bot.py    # 记忆代理

memory_store/          # 记忆存储
├── resources.json     # 原始对话
├── items.json         # 记忆项
└── categories.json    # 分类
```

## 记忆类型

Agent 会自动从对话中提取以下类型的记忆：

| 类型 | 说明 | 示例 |
|------|------|------|
| fact | 事实信息 | "用户的名字是小明" |
| preference | 用户偏好 | "用户喜欢学习Python" |
| skill | 技能/能力 | "用户会使用Git" |
| intent | 意图/目标 | "用户想学习异步编程" |
| todo | 待办事项 | "用户要完成项目报告" |

## 开发

### 运行测试

```bash
uv run pytest tests/ -v
```

### 添加依赖

```bash
uv add <package>
uv add --dev <package>
```

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DASHSCOPE_API_KEY | LLM API Key | (必填) |
| DASHSCOPE_BASE_URL | API Base URL | https://coding.dashscope.aliyuncs.com/v1 |
| DASHSCOPE_MODEL | 模型名称 | kimi-k2.5 |
| MEMORY_STORE_PATH | 记忆存储路径 | ./memory_store |
| MODE | 存储模式 | local |
| VERBOSE | 详细输出 | false |

## License

MIT
