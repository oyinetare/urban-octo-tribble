import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.models import Document, User

# Test database URL - use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Override database dependency for tests
@pytest.fixture(autouse=True)
def override_get_session(async_session):
    """Override get_session dependency for tests."""
    from app.dependencies import get_session
    from app.main import app

    async def get_test_session():
        yield async_session

    app.dependency_overrides[get_session] = get_test_session
    yield
    app.dependency_overrides.clear()


# Create test engine
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_maker = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


# User fixtures
@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user for authentication."""
    user = User(
        email="test@example.com",
        username="testuser",
        # hashed_password=token_manager.get_password_hash("testpassword"),
        hashed_password="",
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# Document fixtures
@pytest_asyncio.fixture
async def test_document(async_session: AsyncSession, test_user: User) -> Document:
    """Create a test user for authentication."""
    document = Document(
        title="Test Document",
        description="Test description",
        owner_id=test_user.id,
    )
    async_session.add(document)
    await async_session.commit()
    await async_session.refresh(document)
    return document
