"""Health check route."""

from fastapi import APIRouter
from meow_agent.service.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse()
