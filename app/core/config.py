from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    # Application
    app_name: str = "RAG Interview Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # Claude
    anthropic_api_key: str
    claude_model: str = "claude-haiku-4-5-20251001"

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Pinecone
    pinecone_api_key: str
    pinecone_index: str = "rag-documents"
    pinecone_namespace: str = "documents"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Database
    database_url: str = "sqlite:///./rag.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()