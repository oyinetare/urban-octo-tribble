from functools import lru_cache

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

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()  # type: ignore[call-arg] # Pydantic loads from env vars
