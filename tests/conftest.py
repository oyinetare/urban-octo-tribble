import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core import services, token_manager
from app.main import app
from app.models import Document, User
from app.services.redis_service import RedisService
from app.services.storage import MockStorageAdapter

# --- Database Setup ---
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


@pytest_asyncio.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with TestSessionLocal() as test_session:
        try:
            yield test_session
        finally:
            await test_session.rollback()
            await test_session.close()
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


# --- Global Mocks (Prevention of Network Calls) ---


@pytest.fixture(scope="session", autouse=True)
def mock_storage_init():
    """Globally block real MinIO initialization."""
    with patch(
        "app.services.storage.MinIOAdapter._ensure_bucket_exists", new_callable=AsyncMock
    ) as m:
        m.return_value = None
        yield m


@pytest.fixture(scope="session", autouse=True)
def mock_embedding_service_global():
    """Globally block heavy ML model loading."""
    with patch(
        "app.services.embeddings.EmbeddingService._ensure_model_loaded", new_callable=AsyncMock
    ) as m:
        m.return_value = None
        yield m


# --- Service Initialization ---


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_services():
    """Unified session initializer: Sets up mocks and calls services.init() ONCE."""
    # 1. Setup Mock Redis
    RedisService._instance = None
    test_redis = RedisService()
    test_redis._redis_client = FakeRedis(decode_responses=True)
    services.redis = test_redis

    # 2. Setup Mock Storage
    mock_s = MockStorageAdapter()
    mock_s._ensure_bucket_exists = AsyncMock(return_value=None)
    services.storage = mock_s

    # 3. Setup Vector Store with Qdrant Mock
    with patch("app.services.vector_store.AsyncQdrantClient") as mock_qdrant_client:
        # Prevent collection check crash
        mock_qdrant_client.return_value.get_collections.return_value = MagicMock(collections=[])

        # Initialize services with a timeout
        await asyncio.wait_for(services.init(), timeout=5.0)
        yield

    # Cleanup
    if services.redis:
        await services.redis.close()


# --- Shared Fixtures ---


@pytest.fixture
def mock_qdrant():
    """Fixture for specific vector store tests to inspect calls."""
    mock_async = MagicMock()
    mock_async.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    mock_async.create_collection = AsyncMock(return_value=True)
    mock_async.upsert = AsyncMock(return_value=True)
    mock_async.delete = AsyncMock(return_value=True)
    mock_async.query_points = AsyncMock()
    return {"async": mock_async}


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession, storage_mock):
    from fakeredis.aioredis import FakeRedis

    from app.core.services import services
    from app.services.redis_service import RedisService

    # 1. Force clear any existing singleton state
    RedisService._instance = None
    test_redis = RedisService()
    test_redis._redis_client = FakeRedis(decode_responses=True)

    # 2. Re-inject mocks
    services.redis = test_redis
    services.storage = storage_mock

    # 3. Use a timeout for the init call to prevent CI hangs
    import asyncio

    try:
        await asyncio.wait_for(services.init(), timeout=5.0)
    except TimeoutError:
        pytest.fail("Service initialization timed out in CI")

    # 4. Standard dependency overrides
    async def override_get_session():
        yield session

    from app.dependencies import get_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_resources():
    """Initialize the Service Container for tests and mock external connections."""
    from unittest.mock import MagicMock, patch

    from app.core.services import services

    # Patch the clients where VectorStoreService imports them
    with (
        patch("app.services.vector_store.QdrantClient") as mock_sync_client,
        patch("app.services.vector_store.AsyncQdrantClient"),
    ):
        # Mock get_collections().collections to return an empty list
        # so _ensure_collection_exists doesn't crash
        mock_sync_client.return_value.get_collections.return_value = MagicMock(collections=[])

        await services.init()
        yield

    # Teardown logic
    if services.redis:
        await services.redis.close()
    if services.vector_store:
        # Use getattr to safely check for the client in case init failed
        async_client = getattr(services.vector_store, "async_client", None)
        if async_client:
            await async_client.close()


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=token_manager.get_password_hash("testpassword"),
        role_name="user",  # Explicit column mapping
        tier_name="free",  # Explicit column mapping
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
        role_name="admin",  # Explicit column mapping
        tier_name="pro",  # Give admins a higher tier
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = token_manager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        tier_limit=test_user.tier.limit,
        scopes=test_user.role.scopes,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    """Get authentication headers for admin user."""
    token = token_manager.create_access_token(
        user_id=admin_user.id,
        username=admin_user.username,
        tier_limit=100,  # Match admin/pro tier
        scopes=["admin", "read", "write"],
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
    with (
        # 1. Patch the tasks at their SOURCE (app.tasks)
        # This intercepts 'from app.tasks import ...' even inside functions
        patch("app.tasks.process_document") as mock_process,
        patch("app.tasks.chunk_document") as mock_chunk,
        # 2. Patch the Celery app instance
        patch("app.celery_app.celery_app.send_task"),
        # 3. Prevent background Redis connection attempts
        patch("celery.app.task.Task.backend", None),
        patch("celery.app.task.Task.update_state", return_value=None),
    ):
        # Configure a generic Task mock
        mock_task_obj = MagicMock()
        mock_task_obj.id = "mock-task-id"

        # Ensure both .delay() and .apply_async() return the mock task
        mock_process.delay.return_value = mock_task_obj
        mock_process.apply_async.return_value = mock_task_obj

        mock_chunk.delay.return_value = mock_task_obj
        mock_chunk.apply_async.return_value = mock_task_obj

        yield {"process_task": mock_process, "chunk_task": mock_chunk, "task_id": "mock-task-id"}


@pytest_asyncio.fixture(scope="session", autouse=True)
async def manage_test_services():
    """Centralized service management for the entire test session."""
    from unittest.mock import MagicMock, patch

    from fakeredis.aioredis import FakeRedis

    from app.core.services import services
    from app.services.redis_service import RedisService

    # 1. Setup Redis Singleton with FakeRedis
    RedisService._instance = None
    test_redis = RedisService()
    test_redis._redis_client = FakeRedis(decode_responses=True)
    services.redis = test_redis

    # 2. MOCK QDRANT CLIENTS
    # We mock both because your service uses Sync for init and Async for ops
    with (
        patch("app.services.vector_store.QdrantClient") as mock_sync_qdrant,
        patch("app.services.vector_store.AsyncQdrantClient"),
    ):
        # Prevent _ensure_collection_exists from crashing by mocking get_collections
        mock_sync_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])

        # 3. Now it's safe to initialize
        await services.init()

    yield

    # 4. Teardown
    if services.redis:
        await services.redis.close()
