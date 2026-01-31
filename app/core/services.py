import logging

from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.services.redis_service import RedisService
from app.services.storage import MinIOAdapter, StorageAdapter
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
settings = get_settings()


class Services:
    storage: StorageAdapter | None = None
    embedding: EmbeddingService | None = None
    vector_store: VectorStoreService | None = None
    redis: RedisService | None = None

    @classmethod
    async def init(cls):
        """Initialize all services with proper error handling"""

        # 1. Redis (Initialize first as it's often a dependency for others)
        if cls.redis is None:
            try:
                cls.redis = RedisService()
                await cls.redis.initialize()
                logger.info("✅ Redis initialized successfully")
            except Exception as e:
                logger.error(f"❌ Redis initialization failed: {e}")
                cls.redis = None

        # 2. Storage
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

        # 3. Embedding
        if cls.embedding is None:
            try:
                cls.embedding = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
                await cls.embedding._ensure_model_loaded()
                logger.info("✅ Embedding service initialized successfully")
            except Exception as e:
                logger.error(f"❌ Embedding initialization failed: {e}")
                cls.embedding = None

        # 4. Vector Store
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


services = Services()
