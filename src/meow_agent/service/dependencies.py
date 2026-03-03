"""Dependency injection for MemU Service."""

import time
from memu.app import MemoryService
from meow_agent.core.config import settings

_memory_service: MemoryService | None = None
_retrieve_cache: dict = {}
_cache_ttl = 300

# 动态配置
_current_retrieve_mode = "fast"  # 默认快速模式


def get_memory_service() -> MemoryService:
    """Provide memU MemoryService singleton instance."""
    global _memory_service

    if _memory_service is None:
        llm_profiles = {
            "default": {
                "api_key": settings.dashscope_api_key,
                "base_url": settings.dashscope_base_url,
                "chat_model": settings.dashscope_model,
            }
        }

        if settings.embedding_api_key and settings.embedding_base_url:
            llm_profiles["embedding"] = {
                "api_key": settings.embedding_api_key,
                "base_url": settings.embedding_base_url,
                "embed_model": settings.embedding_model,
            }
            if settings.verbose:
                print(f"[MemU Service] Using custom embedding: {settings.embedding_base_url}")
                print(f"[MemU Service] Embedding model: {settings.embedding_model}")
        else:
            llm_profiles["embedding"] = {
                "api_key": settings.dashscope_api_key,
                "base_url": settings.dashscope_base_url,
                "embed_model": "text-embedding-ada-002",
            }
            if settings.verbose:
                print(f"[MemU Service] WARNING: Using chat endpoint for embeddings (may be slow)")

        if settings.database_url:
            database_config = {
                "metadata_store": {
                    "provider": "postgres",
                    "dsn": settings.database_url,
                    "ddl_mode": "create",
                }
            }
            if settings.verbose:
                print(f"[MemU Service] Using PostgreSQL for persistent storage")
        else:
            database_config = {
                "metadata_store": {"provider": "inmemory"}
            }
            if settings.verbose:
                print(f"[MemU Service] Using inmemory storage (data will be lost on restart)")

        # 默认使用快速模式
        _memory_service = MemoryService(
            llm_profiles=llm_profiles,
            database_config=database_config,
            retrieve_config={
                "method": "rag",
                "route_intention": False,
                "sufficiency_check": False,
            },
        )
        
        if settings.verbose:
            print(f"[MemU Service] MemoryService initialized successfully")
            print(f"[MemU Service] Default retrieve mode: fast (rag)")

    return _memory_service


def set_retrieve_mode(mode: str) -> dict:
    """Set retrieve mode dynamically.
    
    Args:
        mode: "fast" (rag without LLM) or "smart" (rag with LLM) or "llm"
    
    Returns:
        Updated config info
    """
    global _current_retrieve_mode, _memory_service
    
    if _memory_service is None:
        raise RuntimeError("MemoryService not initialized")
    
    if mode == "fast":
        # 快速模式：纯向量搜索
        _memory_service.retrieve_config.method = "rag"
        _memory_service.retrieve_config.route_intention = False
        _memory_service.retrieve_config.sufficiency_check = False
        _current_retrieve_mode = "fast"
        desc = "Fast mode: Vector search only (~0.2-1s)"
    elif mode == "smart":
        # 智能模式：向量搜索 + LLM 判断
        _memory_service.retrieve_config.method = "rag"
        _memory_service.retrieve_config.route_intention = True
        _memory_service.retrieve_config.sufficiency_check = True
        _current_retrieve_mode = "smart"
        desc = "Smart mode: Vector search with LLM judgment (~5-10s)"
    elif mode == "llm":
        # LLM 模式：完全使用 LLM
        _memory_service.retrieve_config.method = "llm"
        _memory_service.retrieve_config.route_intention = True
        _memory_service.retrieve_config.sufficiency_check = True
        _current_retrieve_mode = "llm"
        desc = "LLM mode: Full LLM-based retrieval (~10-15s)"
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'fast', 'smart', or 'llm'")
    
    if settings.verbose:
        print(f"[MemU Service] Retrieve mode changed to: {mode}")
        print(f"[MemU Service] {desc}")
    
    return {
        "mode": mode,
        "description": desc,
        "config": {
            "method": _memory_service.retrieve_config.method,
            "route_intention": _memory_service.retrieve_config.route_intention,
            "sufficiency_check": _memory_service.retrieve_config.sufficiency_check,
        }
    }


def get_retrieve_mode() -> str:
    """Get current retrieve mode."""
    return _current_retrieve_mode


def get_cache_key(query: str, session_id: str) -> str:
    """Generate cache key."""
    return f"{session_id}:{query}"


def get_cached_result(key: str) -> dict | None:
    """Get cached result if not expired."""
    if key in _retrieve_cache:
        cached_time, result = _retrieve_cache[key]
        if time.time() - cached_time < _cache_ttl:
            return result
        else:
            del _retrieve_cache[key]
    return None


def set_cached_result(key: str, result: dict):
    """Cache result."""
    _retrieve_cache[key] = (time.time(), result)


def clear_cache():
    """Clear all cached results."""
    global _retrieve_cache
    _retrieve_cache = {}
    if settings.verbose:
        print(f"[MemU Service] Cache cleared")
