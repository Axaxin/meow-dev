"""Configuration routes for MemU Service."""

from fastapi import APIRouter, HTTPException
from meow_agent.service.dependencies import (
    set_retrieve_mode,
    get_retrieve_mode,
    clear_cache,
)
from meow_agent.core.config import settings
from pydantic import BaseModel, Field

router = APIRouter()


class SetModeRequest(BaseModel):
    """Request model for setting retrieve mode."""

    mode: str = Field(
        ...,
        description="Retrieve mode: 'fast' (vector only), 'smart' (vector + LLM), or 'llm' (full LLM)",
    )


class SetModeResponse(BaseModel):
    """Response model for setting retrieve mode."""

    mode: str
    description: str
    config: dict


class ConfigInfoResponse(BaseModel):
    """Response model for config info."""

    retrieve_mode: str
    cache_size: int
    verbose: bool


@router.post("/config/retrieve-mode", response_model=SetModeResponse)
async def set_retrieve_mode_endpoint(request: SetModeRequest):
    """Set retrieve mode dynamically.
    
    Modes:
    - **fast**: Vector search only (~0.2-1s) - Best for most cases
    - **smart**: Vector search + LLM judgment (~5-10s) - More intelligent
    - **llm**: Full LLM-based retrieval (~10-15s) - Most intelligent but slowest
    
    Example:
        POST /api/v1/config/retrieve-mode
        {"mode": "fast"}
    """
    try:
        result = set_retrieve_mode(request.mode)
        return SetModeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if settings.verbose:
            print(f"[Config] Error setting mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=ConfigInfoResponse)
async def get_config_info():
    """Get current configuration info."""
    from meow_agent.service.dependencies import _retrieve_cache, _current_retrieve_mode
    
    return ConfigInfoResponse(
        retrieve_mode=_current_retrieve_mode,
        cache_size=len(_retrieve_cache),
        verbose=settings.verbose,
    )


@router.post("/config/clear-cache")
async def clear_cache_endpoint():
    """Clear retrieve cache."""
    try:
        clear_cache()
        return {"success": True, "message": "Cache cleared"}
    except Exception as e:
        if settings.verbose:
            print(f"[Config] Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
