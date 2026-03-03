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

    # Embedding settings (optional - memU has defaults)
    # Required for memU to work properly
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
        description="Embedding model name (e.g., text-embedding-nomic-embed-text-v1.5)",
    )

    # Memory settings
    memory_store_path: str = Field(
        default="./memory_store",
        description="Path to memory storage directory",
    )
    
    # Database settings (for persistent storage)
    database_url: str = Field(
        default="",
        description="Database URL for persistent storage (e.g., postgresql://user:pass@localhost:5432/memu)",
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
