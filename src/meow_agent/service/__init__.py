"""MemU Service - FastAPI application."""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from meow_agent.service.routes import memory, health, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print("🚀 MemU Service starting...")
    yield
    print("👋 MemU Service shutting down...")


app = FastAPI(
    lifespan=lifespan,
    title="MemU Service",
    description="独立的记忆存储/检索服务",
    version="1.1.0",
)

app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
app.include_router(config.router, prefix="/api/v1", tags=["config"])
app.include_router(health.router, tags=["health"])
