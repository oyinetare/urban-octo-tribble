import warnings
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core import get_session, redis_service, token_manager
from app.dependencies import get_storage_service
from app.main import app
from app.models import Document, User
from app.services import DocumentChunker, MockStorageAdapter, StorageAdapter

# Suppress specific warnings at module level
warnings.filterwarnings("ignore", message="coroutine.*was never awaited")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="asyncpg")
warnings.filterwarnings("ignore", message="coroutine 'Connection._cancel' was never awaited")


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # fixes concurrent session issues
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# @pytest.fixture(scope="session")
# def event_loop():
#     """Create event loop and ensure engine disposal happens inside it."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop

#     # Run cleanup explicitly before closing
#     try:
#         # If engine wasn't disposed yet, force it here
#         loop.run_until_complete(test_engine.dispose())

#         pending = asyncio.all_tasks(loop)
#         if pending:
#             loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
#     finally:
#         loop.close()


@pytest_asyncio.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with guaranteed cleanup."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Provide session
    async with TestSessionLocal() as test_session:
        try:
            yield test_session
        finally:
            await test_session.rollback()
            await test_session.close()

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    # This helps clear the StaticPool's single connection
    await test_engine.dispose()


@pytest_asyncio.fixture
async def storage_mock():
    return MockStorageAdapter()


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession, storage_mock: StorageAdapter):
    """Create test client with database and storage overrides."""

    # Define async overrides to match the expected signature of the dependencies
    async def override_get_session():
        yield session

    async def override_get_storage():
        yield storage_mock

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage_service] = override_get_storage

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        try:
            yield ac
        finally:
            app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_resources():
    """Initialize and cleanup resources once for the whole session."""
    await redis_service.initialize()
    yield

    # The session-scoped loop is still open here because of your pytest.ini
    if redis_service.client:
        # close() calls self._redis_client.aclose() which handles the pool
        await redis_service.close()
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
    """
    Create a test document.
    Uses processing_status instead of status to match the model.
    """
    document = Document(
        title="Test Document",
        description="Test Description",
        content="Test Content",
        filename="test_file.pdf",
        storage_key="uploads/test_key",
        file_size=1024,
        content_type="application/pdf",
        owner_id=test_user.id,
        processing_status="pending",
        task_id="task_id",
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """
    Globally mocks Celery task execution to prevent connection
    attempts to Redis/Broker during tests.
    """
    # Replace 'app.tasks.document_processing' with the actual path
    # where your process_document task is defined.
    with (
        patch("app.tasks.document_processing.process_document.delay") as mock_delay,
        patch("app.tasks.document_processing.process_document.apply_async") as mock_apply,
        # Patch the Celery app's connection/backend
        patch("app.celery_app.celery_app.send_task"),
        # Ensure update_state doesn't try to touch Redis
        patch("celery.app.task.Task.update_state", return_value=None),
    ):
        # Configure the mock to return a dummy task object
        mock_task = MagicMock()
        mock_task.id = "mock-task-id"
        mock_delay.return_value = mock_task
        mock_apply.return_value = mock_task

        yield {"delay": mock_delay, "apply": mock_apply}


@pytest_asyncio.fixture
def chunker():
    return DocumentChunker(chunk_size=10, overlap=2)


@pytest.fixture(autouse=True)
def mock_redis_connection():
    with patch("redis.asyncio.Redis.from_url") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_redis_pool():
    """Prevent the actual Redis connection pool from ever starting."""
    with patch("redis.asyncio.connection.ConnectionPool.from_url") as mock:
        mock.return_value = MagicMock()
        yield mock


# @pytest.fixture(scope="session", autouse=True)
# def disable_rate_limits():
#     """Environment override to disable rate limiting logic in tests."""
#     os.environ["RATE_LIMIT_ENABLED"] = "False"
