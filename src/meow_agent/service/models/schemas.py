"""Pydantic models for MemU Service API."""

from pydantic import BaseModel, Field
from typing import Any


class MemorizeRequest(BaseModel):
    """Request model for memorize endpoint."""

    session_id: str = Field(..., description="Session identifier")
    input_text: str = Field(..., description="User input text")
    output_text: str = Field(..., description="Agent output text")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata"
    )


class MemorizeResponse(BaseModel):
    """Response model for memorize endpoint."""

    resource_id: str = Field(..., description="Resource ID")
    items_extracted: int = Field(default=0, description="Number of items extracted")
    success: bool = Field(..., description="Success flag")


class RetrieveRequest(BaseModel):
    """Request model for retrieve endpoint."""

    query: str = Field(..., description="Query string")
    session_id: str = Field(..., description="Session identifier")
    top_k: int = Field(default=5, description="Number of results")


class RetrieveResponse(BaseModel):
    """Response model for retrieve endpoint."""

    items: list[dict[str, Any]] = Field(default_factory=list)
    categories: list[dict[str, Any]] = Field(default_factory=list)
    llm_context: str = Field(default="")


class MemoryListResponse(BaseModel):
    """Response model for list memories endpoint."""

    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = Field(..., description="Total number of items")
    session_id: str = Field(..., description="Session identifier")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = "healthy"
    service: str = "memu-service"
    version: str = "1.1.0"
