import warnings
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.core import get_settings, services, token_manager
from app.main import app
from app.models import Document, User
from app.services import DocumentChunker, MockStorageAdapter

settings = get_settings()

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
    """Initialize the Service Container for tests."""
    # Force a 'testing' state if you added that to your init logic
    await services.init()
    yield
    if services.redis:
        await services.redis.close()
    if services.vector_store:
        await services.vector_store.async_client.close()


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


@pytest_asyncio.fixture
def chunker():
    return DocumentChunker(chunk_size=10, overlap=2)


@pytest.fixture(autouse=True)
def mock_token_bucket():
    """
    Mocks the TokenBucket consume method to prevent real Redis interaction
    and time-based logic during tests.
    """
    # Path should point to where TokenBucket is defined/used
    with patch("app.middleware.rate_limit.TokenBucket.consume") as mock_consume:
        # Default to allowing the request: (allowed=True, info_dict)
        mock_consume.return_value = (True, {"remaining": 10})
        yield mock_consume


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


# Add this fixture to your conftest.py
@pytest.fixture(scope="session", autouse=True)
def mock_embedding_service():
    """Stop sentence-transformers from loading during tests."""
    with patch("app.services.embeddings.EmbeddingService") as mock:
        # Mock the dimension return value
        mock_instance = mock.return_value
        mock_instance.get_embedding_dimension.return_value = 384
        # Mock the batch return (return empty lists or zeros)
        mock_instance.embed_batch.return_value = [[0.0] * 384]
        yield mock


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


# @pytest.fixture(autouse=True)
# def mock_redis_pool():
#     """Prevent the actual Redis connection pool from ever starting."""
#     with patch("redis.asyncio.connection.ConnectionPool.from_url") as mock:
#         mock.return_value = MagicMock()
#         yield mock


# @pytest.fixture(autouse=True)
# def mock_redis_connection():
#     with patch("redis.asyncio.Redis.from_url") as mock:
#         mock.return_value = MagicMock()
#         yield mock


# @pytest.fixture(autouse=True)
# def mock_rate_limiter():
#     """
#     Prevents the rate limiter from actually hitting Redis and
#     allows us to control the 429 responses in tests.
#     """
#     # Adjust this path to where your RateLimitMiddleware or
#     # dependency check lives (e.g., app.middleware.rate_limit)
#     with patch("app.middleware.rate_limit.rate_limit_middleware") as mock_check:
#         # Default to allowing all requests
#         mock_check.return_value = False
#         yield mock_check


# @pytest_asyncio.fixture(scope="session", autouse=True)
# async def setup_qdrant():
#     """
#     Ensures the Qdrant collection exists before running tests.
#     Scope is 'session' so it only runs once.
#     """
#     client = AsyncQdrantClient(
#         host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, api_key=settings.QDRANT_API_KEY
#     )

#     collection_name = settings.QDRANT_COLLECTION_NAME

#     # Check if collection exists
#     collections = await client.get_collections()
#     exists = any(c.name == collection_name for c in collections.collections)

#     if not exists:
#         await client.create_collection(
#             collection_name=collection_name,
#             vectors_config=models.VectorParams(
#                 size=settings.EMBEDDING_DIMENSION, distance=models.Distance.COSINE
#             ),
#         )

#     yield client

#     # Optional: Clean up after the whole test session
#     # await client.delete_collection(collection_name)
#     await client.close()


# @pytest_asyncio.fixture
# async def clean_qdrant(setup_qdrant):
#     """
#     Use this fixture in specific tests to wipe data between runs
#     without deleting the whole collection schema.
#     """
#     await setup_qdrant.delete_payload(
#         collection_name=settings.QDRANT_COLLECTION_NAME,
#         keys_filter=models.Filter(must=[models.HasIdCondition(has_id=[...])]),  # or points selector
#         points=models.FilterSelector(filter=models.Filter()),
#     )
#     yield


# @pytest.fixture(scope="session", autouse=True)
# def disable_rate_limits():
#     """Environment override to disable rate limiting logic in tests."""
#     os.environ["RATE_LIMIT_ENABLED"] = "False"
