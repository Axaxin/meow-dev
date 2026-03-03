# AGENTS.md

This file provides guidance to AI coding agents working on this repository.

## Project Overview

**MemU Service + CLI Client** - A memory storage service with independent CLI client, using the memU framework.

**Current Version**: v1.1.0

**Architecture**:
- **MemU Service**: Independent FastAPI service (port 8000)
- **CLI Client**: Single-file client (cli.py)
- **Memory Storage**: PostgreSQL + pgvector (via memU SDK)

**Tech Stack:**
- Python 3.13+
- Package Manager: uv
- LLM Backend: DashScope (OpenAI-compatible endpoint)
- Memory Framework: memU SDK (official)
- Database: PostgreSQL + pgvector
- API Framework: FastAPI
- Testing: pytest with pytest-asyncio

## Build/Lint/Test Commands

### Initial Setup
```bash
# Install dependencies
uv sync

# Copy environment file and configure API keys
cp .env.example .env

# Edit .env with your API keys
# IMPORTANT: You must set DASHSCOPE_API_KEY to use the service
# Example:
# DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
# DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
# DASHSCOPE_MODEL=gpt-4o-mini
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/memu

# Verify installation
uv run python -c "from meow_agent.service import app; print('OK')"
```

### Running the Application

**Terminal 1 - Start MemU Service:**
```bash
# Start service (default port 8000)
uv run service.py

# Or use uvicorn directly
uv run uvicorn src.meow_agent.service:app --host 0.0.0.0 --port 8000 --reload

# Or use installed script
uv run memu-service
```

**Terminal 2 - Start CLI Client:**
```bash
# Start CLI (auto-configures to smart mode)
uv run cli.py
```

### Dynamic Configuration

```bash
# Switch to fast mode (recommended for most cases)
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"fast"}'

# Switch to smart mode (more intelligent, slower)
curl -X POST http://localhost:8000/api/v1/config/retrieve-mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"smart"}'

# View current configuration
curl http://localhost:8000/api/v1/config
```

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run a single test file
uv run pytest tests/test_basic.py -v

# Run a single test class
uv run pytest tests/test_basic.py::TestModels -v

# Run a single test function
uv run pytest tests/test_basic.py::TestModels::test_resource -v

# Run tests with output
uv run pytest tests/ -v -s

# Run specific test with pattern matching
uv run pytest tests/ -v -k "test_memory"
```

### Dependency Management
```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Update dependencies
uv lock --upgrade
```

### Type Checking and Linting
```bash
# Note: No type checker or linter is currently configured
# Consider using mypy for type checking:
# uv add --dev mypy
# uv run mypy src/

# Consider using ruff for linting:
# uv add --dev ruff
# uv run ruff check src/
```

## Code Style Guidelines

### Imports
Import order (separated by blank lines):
1. Standard library imports
2. Third-party imports
3. Local imports

```python
# Standard library
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Third-party
import numpy as np
from openai import AsyncOpenAI
from pydantic import Field
from pydantic_settings import BaseSettings

# Local imports
from meow_agent.core.config import settings
from meow_agent.core.models import RetrievedContext
from meow_agent.service.client import MemUServiceClient
```

### Formatting
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use double quotes for strings
- No trailing whitespace
- Blank line at end of file
- Use f-strings for string formatting
- Use trailing commas in multi-line lists/dicts/args

### Type Annotations
- Always use type annotations for function parameters and return types
- Use `list[Type]` and `dict[KeyType, ValueType]` (not `List`, `Dict`)
- Use `str | None` instead of `Optional[str]`
- Use `Any` sparingly, prefer specific types

```python
# Good
def create_resource(self, data: dict[str, Any]) -> dict[str, Any]:
    ...

async def handle(self, user_query: str, session_id: str) -> Response:
    ...

def get_resource(self, resource_id: str) -> dict[str, Any] | None:
    ...

# Avoid
def create_resource(data):
    ...
```

### Naming Conventions
- **Files**: `snake_case.py` (e.g., `local_store.py`, `main_agent.py`)
- **Classes**: `PascalCase` (e.g., `MainAgent`, `LocalMemoryStore`)
- **Functions/Methods**: `snake_case` (e.g., `create_resource`, `get_embedding`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_ITEMS`, `DEFAULT_TIMEOUT`)
- **Private methods**: `_leading_underscore` (e.g., `_load`, `_save`, `_get_embedding`)
- **Variables**: `snake_case` (e.g., `resource_id`, `session_id`)

### Docstrings
- Use triple double quotes (`"""`)
- First line should be a brief summary
- Include `Args:` and `Returns:` sections for complex functions
- Use Chinese for user-facing documentation, English for code comments

```python
def create_resource(self, data: dict[str, Any]) -> dict[str, Any]:
    """Create a new resource.
    
    Args:
        data: Resource data dictionary.
    
    Returns:
        Created resource with assigned ID.
    """
    resource_id = f"res_{len(self.resources) + 1:06d}"
    resource = {"id": resource_id, **data}
    self.resources.append(resource)
    self._save()
    return resource
```

### Error Handling
- Use try/except blocks for operations that may fail
- Log errors verbosely when `settings.verbose` is True
- Return sensible defaults on failure (e.g., empty list, None)
- Never let errors crash the application silently

```python
try:
    response = await self.llm.chat.completions.create(...)
    return response.choices[0].message.content
except Exception as e:
    if settings.verbose:
        print(f"Error generating response: {e}")
    return "抱歉，生成回答时出现错误。请稍后再试。"
```

### Async/Await
- Use `async/await` for all I/O operations
- Use `AsyncOpenAI` instead of synchronous `OpenAI` client
- Use `asyncio.create_task()` for fire-and-forget operations
- Use `asyncio.gather()` for concurrent operations

```python
# Fire-and-forget
task = asyncio.create_task(self.memu.memorize_interaction(...))
self._pending_tasks.append(task)

# Concurrent execution
await asyncio.gather(*tasks, return_exceptions=True)
```

### Data Models
- Use `@dataclass` for simple data structures
- Use `pydantic.BaseSettings` for configuration
- Use `Enum` for fixed sets of values
- Include default values with `field(default_factory=...)` for mutable types

```python
@dataclass
class MemoryItem:
    """Layer 2: Fine-grained memory extraction."""
    id: str
    resource_id: str
    type: MemoryItemType
    content: str
    embedding: list[float] = field(default_factory=list)
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)
```

### File Organization
- One class per file for major components
- Group related functions in modules
- Use `__init__.py` to expose public API
- Keep modules focused and cohesive

### Configuration
- Use `pydantic-settings` for configuration management
- Load from `.env` file
- Access via global `settings` instance
- Document all settings with `Field(description=...)`

### Testing
- Use `pytest` for all tests
- Use `@pytest.fixture` for test setup
- Use descriptive test names: `test_<what>_<condition>`
- Use `tmp_path` fixture for file system tests
- Test both success and failure cases

```python
class TestLocalMemoryStore:
    """Test local memory store."""
    
    @pytest.fixture
    def store(self, tmp_path):
        """Create a local memory store."""
        return LocalMemoryStore(str(tmp_path / "memory_store"))
    
    def test_create_resource(self, store):
        """Test creating a resource."""
        resource = store.create_resource({...})
        assert resource["id"].startswith("res_")
```

## Project-Specific Guidelines

### Memory Architecture
This project implements a three-layer memory system using the memU framework:
1. **Resource Layer**: Raw conversation data (JSON input)
2. **Memory Item Layer**: Extracted facts, preferences, skills, intents, todos (auto-extracted by memU)
3. **Category Layer**: Thematic organization (auto-generated Markdown files)

When working with memory:
- Use memU SDK's `memorize()` and `retrieve()` methods
- Memory items are automatically extracted and categorized
- Embeddings are generated automatically by memU
- Categories are organized as Markdown files in `memory/` directory

### LLM Integration
- Use DashScope OpenAI-compatible endpoint
- memU framework handles LLM calls for memory extraction
- Configure via `llm_profiles` in MemoryService
- Set appropriate temperature (0.3-0.7)

### Memory Storage
- Uses memU framework's built-in storage
- Memories stored as Markdown files in hierarchical structure
- File structure: `memory/{category}/{subcategory}.md`
- Files are automatically generated and organized by memU
- Can directly read and edit Markdown files for manual adjustments

### Embedding Configuration
- memU handles embedding generation automatically
- Optional: Configure custom embedding provider via `EMBEDDING_*` variables
- If not configured, memU uses its default embedding model
- **IMPORTANT**: memU manages embeddings internally, no manual migration needed

### Event Bus Pattern
- Use `EventBus` for component communication
- Publish events with `publish_*` methods
- Subscribe with `subscribe()` async iterator
- Always call `stop()` to cleanup

## Common Patterns

### Using memU SDK
```python
from memu.app import MemoryService

# Initialize
service = MemoryService(
    llm_profiles={
        "default": {
            "api_key": settings.dashscope_api_key,
            "base_url": settings.dashscope_base_url,
            "chat_model": settings.dashscope_model,
        }
    }
)

# Memorize conversation
result = await service.memorize(
    resource_url="path/to/conversation.json",
    modality="conversation",
    user={"user_id": session_id}
)

# Retrieve memories
result = await service.retrieve(
    queries=[{"role": "user", "content": {"text": query}}],
    where={"user_id": session_id},
    method="rag"  # or "llm"
)
```

### Adding a New Memory Type
1. Add to `memorize_config["memory_types"]` list
2. Optionally add custom prompt in `memorize_config["memory_type_prompts"]`
3. memU will automatically extract and categorize

### Adding Configuration
1. Add field to `Settings` class in `config.py`
2. Add to `.env.example`
3. Pass to memU MemoryService initialization

## Important Notes

- Always run tests before committing: `uv run pytest tests/ -v`
- Memory storage operations are async - wait for completion before exit
- Use `settings.verbose` to control logging verbosity
- JSON files use UTF-8 encoding and 2-space indentation
- IDs use format: `res_000001`, `item_000001`, `cat_000001`
- Test memory recall after configuration changes: `uv run main.py --session-id test`
