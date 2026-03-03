"""Memory routes for MemU Service."""

import tempfile
import json
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from memu.app import MemoryService
from meow_agent.service.models.schemas import (
    MemorizeRequest,
    MemorizeResponse,
    RetrieveRequest,
    RetrieveResponse,
    MemoryListResponse,
)
from meow_agent.service.dependencies import get_memory_service
from meow_agent.core.config import settings

router = APIRouter()


@router.post("/memorize", response_model=MemorizeResponse)
async def memorize(
    request: MemorizeRequest, memu: MemoryService = Depends(get_memory_service)
):
    """Store conversation to memory system."""
    try:
        if settings.verbose:
            print(f"[MemU Service] Memorize request from session: {request.session_id}")
            print(f"[MemU Service] Input: {request.input_text[:50]}...")
        
        conversation_data = {
            "messages": [
                {"role": "user", "content": request.input_text},
                {"role": "assistant", "content": request.output_text},
            ],
            "metadata": request.metadata or {},
            "session_id": request.session_id,
        }

        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(conversation_data, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()

        try:
            if settings.verbose:
                print(f"[MemU Service] Calling memU SDK memorize()...")
            
            result = await memu.memorize(
                resource_url=temp_file.name,
                modality="conversation",
                user={"user_id": request.session_id},
            )

            resource_id = result.get("resource", {}).get("id", "")
            items_count = len(result.get("items", []))

            if settings.verbose:
                print(
                    f"[MemU Service] ✅ Memorized: {resource_id}, items: {items_count}"
                )

            return MemorizeResponse(
                resource_id=resource_id,
                items_extracted=items_count,
                success=bool(resource_id),
            )
        finally:
            Path(temp_file.name).unlink(missing_ok=True)

    except Exception as e:
        if settings.verbose:
            print(f"[MemU Service] ❌ Memorize error: {e}")
            import traceback
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    request: RetrieveRequest, memu: MemoryService = Depends(get_memory_service)
):
    """Retrieve relevant memories.
    
    Uses the current retrieve mode (configured via /api/v1/config/retrieve-mode).
    
    Default mode is "fast" (vector search only, ~0.2-1s).
    """
    from meow_agent.service.dependencies import (
        get_cache_key, get_cached_result, set_cached_result, get_retrieve_mode
    )
    
    # Check cache
    cache_key = get_cache_key(request.query, request.session_id)
    cached = get_cached_result(cache_key)
    if cached:
        if settings.verbose:
            print(f"[MemU Service] ✅ Cache hit for query: {request.query[:30]}...")
        return RetrieveResponse(**cached)
    
    try:
        current_mode = get_retrieve_mode()
        
        if settings.verbose:
            print(f"[MemU Service] Retrieve request from session: {request.session_id}")
            print(f"[MemU Service] Query: {request.query[:50]}...")
            print(f"[MemU Service] Current mode: {current_mode}")
        
        # Call memU SDK
        if settings.verbose:
            if current_mode == "fast":
                print(f"[MemU Service] ⏳ Fast mode: Vector search (~0.2-1s)...")
            elif current_mode == "smart":
                print(f"[MemU Service] ⏳ Smart mode: Vector + LLM judgment (~5-10s)...")
            else:
                print(f"[MemU Service] ⏳ LLM mode: Full LLM retrieval (~10-15s)...")
        
        result = await memu.retrieve(
            queries=[{"role": "user", "content": {"text": request.query}}],
            where={"user_id": request.session_id},
        )

        items = result.get("items", [])
        categories = result.get("categories", [])
        llm_context = result.get("llm_context", "")

        if settings.verbose:
            print(f"[MemU Service] ✅ Retrieved: {len(items)} items, {len(categories)} categories")
            if items:
                for i, item in enumerate(items[:3], 1):
                    print(f"[MemU Service]   {i}. {item.get('memory_type', 'unknown')}: {item.get('summary', '')[:60]}...")

        response_data = {
            "items": items[: request.top_k],
            "categories": categories,
            "llm_context": llm_context
        }
        
        # Cache result
        set_cached_result(cache_key, response_data)
        if settings.verbose:
            print(f"[MemU Service] 💾 Cached result for future queries")

        return RetrieveResponse(**response_data)

    except Exception as e:
        if settings.verbose:
            print(f"[MemU Service] ❌ Retrieve error: {e}")
            import traceback
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories", response_model=MemoryListResponse)
async def list_memories(
    session_id: str = Query(..., description="Session identifier"),
    memory_type: str | None = Query(None, description="Filter by memory type"),
    limit: int = Query(10, ge=1, le=100, description="Limit results"),
    memu: MemoryService = Depends(get_memory_service),
):
    """List memories (Note: memU SDK does not support this yet)."""
    if settings.verbose:
        print("[MemU Service] List memories not supported by memU SDK yet")

    return MemoryListResponse(items=[], total=0, session_id=session_id)


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str, memu: MemoryService = Depends(get_memory_service)
):
    """Delete memory (Note: memU SDK does not support this yet)."""
    if settings.verbose:
        print("[MemU Service] Delete memory not supported by memU SDK yet")

    return {"success": False, "message": "Not supported by memU SDK yet"}
