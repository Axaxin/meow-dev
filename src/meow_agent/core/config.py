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

    # Database settings (for persistent storage)
    database_url: str = Field(
        default="",
        description="Database URL for persistent storage (e.g., postgresql://user:pass@localhost:5432/memu)",
    )

    # DashScope / OpenAI compatible LLM settings (for memU SDK)
    dashscope_api_key: str = Field(default="", description="DashScope API key")
    dashscope_base_url: str = Field(
        default="https://coding.dashscope.aliyuncs.com/v1",
        description="DashScope API base URL",
    )
    dashscope_model: str = Field(
        default="gpt-4o-mini",
        description="Model name to use",
    )

    # Embedding settings (required for memU)
    embedding_api_key: str = Field(
        default="",
        description="Embedding API key (for custom embedding provider)",
    )
    embedding_base_url: str = Field(
        default="",
        description="Embedding API base URL (e.g., http://127.0.0.1:1234/v1)",
    )
    embedding_model: str = Field(
        default="",
        description="Embedding model name (e.g., text-embedding-3-small)",
    )

    # Service settings
    api_host: str = Field(
        default="0.0.0.0",
        description="API service host",
    )
    api_port: int = Field(
        default=8000,
        description="API service port",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )


settings = Settings()
