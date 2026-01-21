import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core import get_session, token_manager
from app.main import app
from app.models import Document, User

# Test database URL (use in-memory SQLite for tests)
# CRITICAL FIX: Use StaticPool for SQLite to avoid session conflicts
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # CRITICAL: This fixes concurrent session issues
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with proper isolation."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Provide session
    async with TestSessionLocal() as test_session:
        yield test_session
        await test_session.rollback()  # Rollback any uncommitted changes

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""

    # This is where 'session' is requested
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    # Using 'testserver' to fix the Host Header issue
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=token_manager.get_password_hash("testpassword"),
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession) -> User:
    """Create an admin user."""
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=token_manager.get_password_hash("adminpassword"),
        role="admin",
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Get authentication headers for test user."""
    token = token_manager.create_access_token(
        data={"sub": test_user.username, "scopes": ["read", "write"]}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    """Get authentication headers for admin user."""
    token = token_manager.create_access_token(
        data={"sub": admin_user.username, "scopes": ["admin", "read", "write"]}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_document(session: AsyncSession, test_user: User) -> Document:
    """Create a test document."""
    document = Document(
        title="Test Document",
        description="Test Description",
        content="Test Content",
        owner_id=test_user.id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document
