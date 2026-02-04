from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str

    # Database
    DATABASE_URL: str

    # Application
    ENVIRONMENT: str = "development"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis (for token blacklisting, caching, rate limiting...)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    # MinIO / S3 Storage
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_DOCUMENTS_BUCKET_NAME: str = "documents"
    MINIO_USE_SSL: bool = False
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str

    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: str = "pdf,txt,doc,docx,md,xlsx,pptx"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_SERIALIZER: str
    CELERY_RESULT_SERIALIZER: str
    CELERY_ACCEPT_CONTENT: list[str]
    CELERY_TIMEZONE: str
    CELERY_ENABLE_UTC: bool
    CELERY_WORKER: bool

    # Qdrant Configuration
    QDRANT_HOST: str = Field(default="qdrant", description="Qdrant host")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant port")
    QDRANT_COLLECTION_NAME: str = Field(
        default="documents", description="Qdrant collection name for documents"
    )
    QDRANT_API_KEY: str | None = Field(
        default=None, description="Optional API key for Qdrant Cloud"
    )

    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence transformer model for embeddings"
    )
    EMBEDDING_DIMENSION: int = Field(default=384, description="Dimension of embedding vectors")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Batch size for embedding generation")

    # Search Configuration
    DEFAULT_SEARCH_LIMIT: int = Field(default=5, description="Default number of search results")
    DEFAULT_SCORE_THRESHOLD: float = Field(
        default=0.7, description="Default minimum similarity score for search"
    )

    # LLM Configuration
    LLM_PROVIDER: str = Field(
        default="ollama", description="Primary LLM provider: 'anthropic' or 'ollama'"
    )
    LLM_FALLBACK_ENABLED: bool = Field(
        default=True, description="Enable fallback to secondary LLM provider"
    )

    # Anthropic Configuration
    ANTHROPIC_API_KEY: str | None = Field(default=None, description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(
        default="claude-sonnet-4-20250514", description="Anthropic model name"
    )
    ANTHROPIC_MAX_TOKENS: int = Field(default=4096, description="Max tokens for Claude responses")
    ANTHROPIC_TEMPERATURE: float = Field(default=0.7, description="Claude temperature (0-1)")

    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Ollama API base URL"
    )
    OLLAMA_MODEL: str = Field(default="llama3.2", description="Ollama model name")
    OLLAMA_TIMEOUT: int = Field(default=120, description="Ollama request timeout in seconds")

    # RAG Configuration
    RAG_MAX_CONTEXT_CHUNKS: int = Field(
        default=5, description="Maximum number of chunks to include in context"
    )
    RAG_MIN_SIMILARITY_SCORE: float = Field(
        default=0.6, description="Minimum similarity score for chunk inclusion"
    )
    RAG_SYSTEM_PROMPT: str = Field(
        default="""You are a helpful AI assistant that answers questions based on the provided document context.

Rules:
1. Answer ONLY based on the provided context
2. If the context doesn't contain enough information, say so
3. Cite your sources by referencing [Source N] where N is the chunk number
4. Be precise and concise
5. If asked about multiple documents, clearly distinguish between sources""",
        description="System prompt for RAG",
    )

    # Hybrid Search Configuration
    HYBRID_SEARCH_ENABLED: bool = Field(
        default=True, description="Enable hybrid search (vector + keyword)"
    )

    HYBRID_RRF_K: int = Field(
        default=60, description="RRF constant for reciprocal rank fusion (typically 60)"
    )

    HYBRID_FETCH_MULTIPLIER: int = Field(
        default=4,
        description="Multiplier for fetching results before RRF fusion (e.g., 4x the limit)",
    )

    FTS_LANGUAGE: str = Field(
        default="english", description="PostgreSQL full-text search language configuration"
    )

    # Event Streaming (Kafka/Redpanda)
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:19092", description="Kafka/Redpanda bootstrap servers (comma-separated)"
    )
    KAFKA_EVENTS_TOPIC: str = Field(
        default="document-events", description="Topic for document lifecycle events"
    )
    KAFKA_ANALYTICS_TOPIC: str = Field(
        default="analytics-events", description="Topic for analytics events"
    )
    KAFKA_CONSUMER_GROUP: str = Field(
        default="urban-octo-tribble-consumers", description="Consumer group ID"
    )
    KAFKA_ENABLE_EVENTS: bool = Field(
        default=True, description="Enable event publishing (disable for testing)"
    )

    # Consistent Hashing / Sharding Configuration
    SHARDING_ENABLED: bool = Field(
        default=True, description="Enable consistent hashing for sharding"
    )
    SHARDING_VIRTUAL_NODES: int = Field(
        default=150, description="Virtual nodes per shard for consistent hashing"
    )
    SHARDING_STRATEGY: str = Field(
        default="user", description="Sharding strategy: 'user' or 'document'"
    )
    # Shard configurations (comma-separated: "shard-1:1,shard-2:1,shard-3:2")
    # Format: "id:weight,id:weight,..."
    SHARD_NODES: str = Field(
        default="shard-0:1", description="Shard node configurations (id:weight pairs)"
    )

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()  # type: ignore[call-arg] # Pydantic loads from env vars
