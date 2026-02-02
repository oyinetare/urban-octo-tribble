import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.core import get_settings

settings = get_settings()


# Detect if we're running in a Celery worker context
# Set CELERY_WORKER=true in your worker environment
IS_CELERY_WORKER = os.getenv("CELERY_WORKER", "false").lower() == "true"


# Create async engine
# Use NullPool for Celery workers to avoid event loop binding issues
# Use default pool for API servers for better performance
if IS_CELERY_WORKER:
    # NullPool doesn't accept pool_size or max_overflow
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
else:
    # Default pool with connection pooling for API
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
