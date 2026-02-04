"""
Service initialization with production optimizations.

Adds:
- Redis for caching (integrated into RedisService)
- MetricsService for performance tracking
- QueryClassifier for smart routing
- EventProducer for event streaming
"""

import logging

from app.core.config import get_settings
from app.services.ai.embeddings import EmbeddingService
from app.services.ai.query_classifier import QueryClassifier
from app.services.ai.rag import RAGService
from app.services.ai.vector_store import VectorStoreService
from app.services.events import EventProducer
from app.services.optimization.metrics_service import MetricsService
from app.services.optimization.redis_service import RedisService
from app.services.optimization.shard_service import ShardService
from app.services.storage import MinIOAdapter, StorageAdapter

logger = logging.getLogger(__name__)
settings = get_settings()


class Services:
    storage: StorageAdapter | None = None
    embedding: EmbeddingService | None = None
    vector_store: VectorStoreService | None = None
    rag: RAGService | None = None
    classifier: QueryClassifier | None = None

    # Optimization services
    metrics: MetricsService | None = None
    redis: RedisService | None = None
    shard_service: ShardService | None = None

    # Event streaming
    events: EventProducer | None = None

    @classmethod
    async def init(cls):
        """Initialize all services with proper error handling"""

        # 1. Redis (Initialize first as it's a dependency for others)
        if cls.redis is None:
            try:
                cls.redis = RedisService()
                await cls.redis.initialize()
                logger.info("✅ Redis initialized successfully")
            except Exception as e:
                logger.error(f"❌ Redis initialization failed: {e}")
                cls.redis = None

        # 2. Initialize metrics service (depends on Redis)
        if cls.metrics is None:
            try:
                cls.metrics = MetricsService(redis=cls.redis)
                if cls.metrics.is_available:
                    logger.info("✅ Metrics service initialized successfully")
                else:
                    logger.warning("⚠️  Metrics service initialized but Redis unavailable")
            except Exception as e:
                logger.error(f"❌ Metrics service initialization failed: {e}")
                cls.metrics = None

        # 3. Initialize query classifier (no dependencies)
        if cls.classifier is None:
            try:
                cls.classifier = QueryClassifier()
                logger.info("✅ Query classifier initialized successfully")
            except Exception as e:
                logger.error(f"❌ Query classifier initialization failed: {e}")
                cls.classifier = None

        # 4. Initialize event producer (no dependencies)
        if cls.events is None:
            try:
                cls.events = EventProducer()
                await cls.events.initialize()
                if cls.events.is_initialized:
                    logger.info("✅ Event producer initialized successfully")
                else:
                    logger.warning("⚠️  Event producer disabled or failed to initialize")
            except Exception as e:
                logger.error(f"❌ Event producer initialization failed: {e}")
                cls.events = None

        # 5. Storage
        if cls.storage is None:
            try:
                cls.storage = MinIOAdapter(
                    endpoint=settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    bucket_name=settings.MINIO_DOCUMENTS_BUCKET_NAME,
                    use_ssl=settings.MINIO_USE_SSL,
                )
                await cls.storage._ensure_bucket_exists()
                logger.info("✅ Storage (MinIO) initialized successfully")
            except Exception as e:
                logger.error(f"❌ Storage initialization failed: {e}")
                cls.storage = None

        # Shard service
        if cls.shard_service is None:
            try:
                cls.shard_service = ShardService()
                await cls.shard_service.initialize()
                logger.info("✅ Shard Service initialized successfully")
            except Exception as e:
                logger.error(f"❌ Shard Service initialization failed: {e}")
                cls.classifier = None

        # 6. Embedding
        if cls.embedding is None:
            try:
                cls.embedding = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
                await cls.embedding._ensure_model_loaded()
                logger.info("✅ Embedding service initialized successfully")
            except Exception as e:
                logger.error(f"❌ Embedding initialization failed: {e}")
                cls.embedding = None

        # 7. Vector Store
        if cls.vector_store is None:
            if cls.embedding is None:
                logger.error("❌ Cannot initialize vector store without embedding service")
                return

            cls.vector_store = VectorStoreService(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                collection_name=settings.QDRANT_COLLECTION_NAME,
                embedding_dimension=cls.embedding.get_embedding_dimension(),
            )

            try:
                await cls.vector_store._ensure_collection_exists()
                logger.info("✅ Vector store (Qdrant) initialized successfully")
            except Exception as e:
                logger.error(f"❌ Vector store initialization failed: {e}")
                logger.error(f"   Qdrant host: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
                logger.error(f"   Collection: {settings.QDRANT_COLLECTION_NAME}")
                logger.error(f"   Dimension: {cls.embedding.get_embedding_dimension()}")
                import traceback

                logger.error(traceback.format_exc())
                cls.vector_store = None

        # 8. RAG Service (with optimizations)
        if cls.rag is None:
            assert cls.vector_store is not None, "VectorStore must be initialized"
            assert cls.embedding is not None, "Embedding must be initialized"

            try:
                from app.services.ai.llm import LLMService

                llm = LLMService()

                # Pass optimization services to RAG
                cls.rag = RAGService(
                    vector_store=cls.vector_store,
                    embedding_service=cls.embedding,
                    llm_service=llm,
                    session=None,
                    redis=cls.redis,  # Pass Redis directly
                    metrics_service=cls.metrics,
                    classifier=cls.classifier,
                )
                logger.info("✅ RAG service initialized successfully")

                # Log optimization status
                if cls.redis and cls.redis.is_available:
                    logger.info("   📦 Response caching: ENABLED (via Redis)")
                else:
                    logger.warning("   📦 Response caching: DISABLED (Redis unavailable)")

                if cls.metrics and cls.metrics.is_available:
                    logger.info("   📊 Performance metrics: ENABLED")
                else:
                    logger.warning("   📊 Performance metrics: DISABLED (Redis unavailable)")

                if cls.classifier:
                    logger.info("   🎯 Query classification: ENABLED")
                else:
                    logger.warning("   🎯 Query classification: DISABLED")

            except Exception as e:
                logger.error(f"❌ RAG initialization failed: {e}")
                import traceback

                logger.error(traceback.format_exc())

    @classmethod
    async def shutdown(cls):
        """Gracefully shutdown all services"""
        logger.info("🔄 Shutting down services...")

        # Close event producer
        if cls.events:
            await cls.events.close()

        # Close Redis
        if cls.redis:
            await cls.redis.close()

        logger.info("✅ All services shut down")


services = Services()
