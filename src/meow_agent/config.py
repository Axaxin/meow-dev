"""Configuration management using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DashScope / OpenAI compatible LLM settings
    dashscope_api_key: str = Field(default="", description="DashScope API key")
    dashscope_base_url: str = Field(
        default="https://coding.dashscope.aliyuncs.com/v1",
        description="DashScope API base URL",
    )
    dashscope_model: str = Field(
        default="kimi-k2.5",
        description="Model name to use",
    )

    # MemU API settings
    memu_api_key: str = Field(default="", description="MemU API key")
    memu_endpoint: str = Field(
        default="https://api.memu.so",
        description="MemU API endpoint",
    )

    # Embedding settings
    embedding_type: str = Field(
        default="api",
        description="Embedding type: 'api' for remote API, 'local' for sentence-transformers",
    )
    embedding_api_key: str = Field(
        default="",
        description="Embedding API key (defaults to dashscope_api_key if not set)",
    )
    embedding_base_url: str = Field(
        default="",
        description="Embedding API base URL (for OpenAI-compatible endpoints)",
    )
    embedding_model: str = Field(
        default="text-embedding-qwen3-embedding-0.6b",
        description="Embedding model name or path",
    )

    # Memory settings
    memory_store_path: str = Field(
        default="./memory_store",
        description="Path to local memory store",
    )

    # Agent settings
    proactive_interval: int = Field(
        default=60,
        description="Interval for proactive tasks in seconds",
    )

    # Runtime settings
    mode: str = Field(
        default="local",
        description="Storage mode: 'local' or 'cloud'",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )


# Global settings instance
settings = Settings()