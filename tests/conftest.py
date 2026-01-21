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
    """Create test database session with guaranteed cleanup."""
    # 1. Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # 2. Provide session with guaranteed closure
    async with TestSessionLocal() as test_session:
        try:
            yield test_session
        finally:
            # This block runs even if the test fails
            await test_session.rollback()
            await test_session.close()  # CRITICAL: Ensures internal coroutines are awaited

    # 3. Drop tables
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
        try:
            yield ac
        finally:
            # Ensure overrides are cleared even if client usage fails
            app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def dispose_engine_after_tests():
    """Explicitly dispose of the engine pool after the full test suite finishes."""
    yield
    # This runs after all tests are finished
    # SQLAlchemy 2.0+ requires explicit disposal for clean async exit
    await test_engine.dispose()


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
