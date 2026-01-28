from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.services.redis_service import RedisService
from app.services.storage import MinIOAdapter, StorageAdapter
from app.services.vector_store import VectorStoreService

settings = get_settings()


class Services:
    storage: StorageAdapter | None = None
    embedding: EmbeddingService | None = None
    vector_store: VectorStoreService | None = None
    redis: RedisService | None = None

    @classmethod
    async def init(cls):
        # 1. Redis (Initialize first as it's often a dependency for others)
        if cls.redis is None:
            cls.redis = RedisService()
            await cls.redis.initialize()

        # 2. Storage
        if cls.storage is None:
            cls.storage = MinIOAdapter(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                bucket_name=settings.MINIO_DOCUMENTS_BUCKET_NAME,
                use_ssl=settings.MINIO_USE_SSL,
            )  # as before

        # 3. Embedding
        if cls.embedding is None:
            cls.embedding = EmbeddingService(model_name=settings.EMBEDDING_MODEL)

        # 4. Vector Store
        if cls.vector_store is None:
            cls.vector_store = VectorStoreService(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                collection_name=settings.QDRANT_COLLECTION_NAME,
                embedding_dimension=cls.embedding.get_embedding_dimension(),
            )


services = Services()
