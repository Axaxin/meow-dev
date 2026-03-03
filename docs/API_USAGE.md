# MemU Service API 使用指南

完整的 API 文档和使用示例。

## 📡 API 端点

### 基础 URL

```
http://localhost:8000
```

### 交互式文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 🎛️ 配置管理 API

### 1. 查看当前配置

**GET /api/v1/config**

查看服务的当前配置状态。

**请求示例：**
```bash
curl http://localhost:8000/api/v1/config
```

**响应示例：**
```json
{
  "retrieve_mode": "smart",
  "cache_size": 5,
  "verbose": false
}
```

**字段说明：**
- `retrieve_mode`: 当前检索模式（fast/smart/llm）
- `cache_size`: 缓存中的结果数量
- `verbose`: 是否启用详细日志

---

### 2. 设置检索模式

**POST /api/v1/config/retrieve-mode**

动态切换检索模式，无需重启服务。

**请求示例：**
```bash
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "smart"}'
```

**模式说明：**

| 模式 | 描述 | 响应时间 | 适用场景 |
|------|------|---------|---------|
| `fast` | 纯向量搜索 | 0.2-1s | 简单对话、快速响应（推荐） |
| `smart` | 向量搜索 + LLM 判断 | 5-10s | 复杂查询、需要智能判断 |
| `llm` | 完全 LLM 检索 | 10-15s | 最智能但最慢 |

**响应示例：**
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

**配置详情：**
- `method`: 检索方法（rag/llm）
- `route_intention`: 是否使用 LLM 判断是否需要检索
- `sufficiency_check`: 是否使用 LLM 判断检索结果是否充分

---

### 3. 清除缓存

**POST /api/v1/config/clear-cache**

清除所有缓存的检索结果。

**请求示例：**
```bash
curl -X POST http://localhost:8000/api/v1/config/clear-cache
```

**响应示例：**
```json
{
  "success": true,
  "message": "Cache cleared"
}
```

---

## 📝 记忆操作 API

### 1. 存储记忆

**POST /api/v1/memorize**

将对话存储到记忆系统中。memU SDK 会自动提取 facts, preferences, skills 等。

**请求示例：**
```bash
curl -X POST http://localhost:8000/api/v1/memorize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_001",
    "input_text": "我喜欢吃提拉米苏",
    "output_text": "好的，我记住了！提拉米苏很美味",
    "metadata": {}
  }'
```

**请求字段：**
- `session_id` (string, required): 会话标识符
- `input_text` (string, required): 用户输入
- `output_text` (string, required): 助手回复
- `metadata` (object, optional): 额外元数据

**响应示例：**
```json
{
  "resource_id": "res_000001",
  "items_extracted": 2,
  "success": true
}
```

**响应字段：**
- `resource_id`: 资源 ID
- `items_extracted`: 提取的记忆项数量
- `success`: 是否成功

**注意事项：**
- 这是一个耗时操作（~15 秒）
- CLI 客户端使用异步后台调用，不阻塞用户
- memU SDK 会自动提取和分类记忆

---

### 2. 检索记忆

**POST /api/v1/retrieve**

根据查询检索相关记忆。使用当前配置的检索模式。

**请求示例：**
```bash
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "用户喜欢什么食物",
    "session_id": "user_001",
    "top_k": 5
  }'
```

**请求字段：**
- `query` (string, required): 查询文本
- `session_id` (string, required): 会话标识符
- `top_k` (integer, optional): 返回结果数量（默认 5）

**响应示例：**
```json
{
  "items": [
    {
      "id": "item_001",
      "memory_type": "preference",
      "summary": "用户喜欢吃提拉米苏",
      "confidence": 0.95,
      "created_at": "2025-03-04T12:00:00Z"
    }
  ],
  "categories": [
    {
      "id": "cat_001",
      "name": "preferences",
      "description": "User preferences, likes and dislikes"
    }
  ],
  "llm_context": ""
}
```

**响应字段：**
- `items`: 记忆项列表
  - `memory_type`: 记忆类型（fact/preference/skill/intent/todo）
  - `summary`: 记忆摘要
  - `confidence`: 置信度
- `categories`: 相关分类
- `llm_context`: LLM 生成的上下文（smart/llm 模式）

---

### 3. 健康检查

**GET /health**

检查服务是否正常运行。

**请求示例：**
```bash
curl http://localhost:8000/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "service": "memu-service",
  "version": "1.1.0"
}
```

---

## 💡 使用示例

### 示例 1: 基础对话流程

```bash
# 1. 启动服务
uv run service.py

# 2. 检查服务状态
curl http://localhost:8000/health

# 3. 设置为快速模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"fast"}'

# 4. 存储对话
curl -X POST http://localhost:8000/api/v1/memorize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo",
    "input_text": "我叫张三",
    "output_text": "你好张三，很高兴认识你！"
  }'

# 5. 检索记忆
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "用户叫什么名字",
    "session_id": "demo",
    "top_k": 3
  }'
```

---

### 示例 2: Python 客户端

```python
import requests

class MemUClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def set_mode(self, mode):
        """设置检索模式"""
        resp = requests.post(
            f"{self.base_url}/api/v1/config/retrieve-mode",
            json={"mode": mode}
        )
        return resp.json()
    
    def memorize(self, session_id, input_text, output_text):
        """存储对话"""
        resp = requests.post(
            f"{self.base_url}/api/v1/memorize",
            json={
                "session_id": session_id,
                "input_text": input_text,
                "output_text": output_text
            }
        )
        return resp.json()
    
    def retrieve(self, query, session_id, top_k=5):
        """检索记忆"""
        resp = requests.post(
            f"{self.base_url}/api/v1/retrieve",
            json={
                "query": query,
                "session_id": session_id,
                "top_k": top_k
            }
        )
        return resp.json()

# 使用示例
client = MemUClient()

# 设置为智能模式
client.set_mode("smart")

# 存储对话
client.memorize("user_001", "我喜欢编程", "好的，我记住了！")

# 检索记忆
memories = client.retrieve("用户喜欢什么", "user_001")
print(f"找到 {len(memories['items'])} 条记忆")
```

---

### 示例 3: 切换模式对比性能

```bash
# 测试快速模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"fast"}'

time curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"测试查询","session_id":"test","top_k":5}'
# 预期: 0.2-1s

# 测试智能模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"smart"}'

time curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"测试查询","session_id":"test","top_k":5}'
# 预期: 5-10s

# 测试缓存（第二次相同查询）
time curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"测试查询","session_id":"test","top_k":5}'
# 预期: 0.02s
```

---

## 🔧 故障排除

### 问题 1: 500 Internal Server Error

**原因**: MemoryService 未初始化

**解决方案**:
```bash
# 先触发一次检索以初始化
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"init","session_id":"init","top_k":1}'

# 然后再设置模式
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"smart"}'
```

---

### 问题 2: 检索速度慢

**检查当前模式**:
```bash
curl http://localhost:8000/api/v1/config
```

**切换到快速模式**:
```bash
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"fast"}'
```

---

### 问题 3: 检索结果不准确

**切换到智能模式**:
```bash
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"smart"}'
```

---

### 问题 4: 缓存占用过多内存

**清除缓存**:
```bash
curl -X POST http://localhost:8000/api/v1/config/clear-cache
```

---

## 📊 性能基准

| 操作 | Fast 模式 | Smart 模式 | LLM 模式 | 缓存命中 |
|------|----------|-----------|---------|---------|
| **检索** | 0.2-1s | 5-10s | 10-15s | 0.02s |
| **存储** | ~15s (后台) | ~15s (后台) | ~15s (后台) | - |
| **总响应** | ~3s | ~8s | ~13s | ~2s |

**推荐配置**:
- 日常使用: `fast` 模式
- 复杂查询: `smart` 模式
- 特殊需求: `llm` 模式

---

## 📝 最佳实践

1. **默认使用 fast 模式**: 90% 的场景下足够
2. **需要时切换到 smart 模式**: 复杂查询或需要更准确的结果
3. **利用缓存**: 相同查询会从缓存读取，极快
4. **异步存储**: memorize 操作耗时长，建议后台异步执行
5. **监控缓存**: 定期检查缓存大小，必要时清除

---

## 🔗 相关链接

- [memU 框架](https://github.com/NevaMind-AI/memU)
- [memU 文档](https://memu.pro/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [项目 README](../README.md)
