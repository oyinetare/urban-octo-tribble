import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HnswConfigDiff,
    MatchValue,
    OptimizersConfigDiff,
    PointStruct,
    VectorParams,
)

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreService:
    """Qdrant vector store for document embeddings"""

    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        embedding_dimension: int,
        api_key: str | None = None,
    ):
        """
        Initialize Qdrant vector store

        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Collection name for documents
            embedding_dimension: Dimension of embeddings
            api_key: Optional API key for Qdrant Cloud
        """
        # We only need the Async client.
        # Avoid performing I/O (like _ensure_collection_exists) in __init__
        self.async_client = AsyncQdrantClient(
            host=host,
            port=port,
            api_key=api_key,
            prefer_grpc=False,
            https=False,
        )

        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension

    async def _ensure_collection_exists(self):
        """
        Create collection if it doesn't exist with optimized HNSW parameters.
        Now async to satisfy the 'await' in Services.init
        """
        try:
            # Test connection first
            logger.info(f"Connecting to Qdrant to check/create collection: {self.collection_name}")

            # Get existing collections
            response = await self.async_client.get_collections()
            collection_names = [col.name for col in response.collections]

            logger.info(f"Found {len(collection_names)} existing collections: {collection_names}")

            if self.collection_name not in collection_names:
                logger.info(
                    f"Creating collection '{self.collection_name}' with dimension {self.embedding_dimension}"
                )

                await self.async_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE,
                    ),
                    hnsw_config=HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        indexing_threshold=10,
                    ),
                )
                logger.info(f"✅ Successfully created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"✅ Collection already exists: {self.collection_name}")

            # Verify the collection was created/exists
            response = await self.async_client.get_collections()
            collection_names = [col.name for col in response.collections]
            if self.collection_name in collection_names:
                logger.info(f"✅ Verified collection '{self.collection_name}' exists in Qdrant")
            else:
                raise Exception(f"Collection '{self.collection_name}' not found after creation")

        except Exception as e:
            logger.error(f"❌ Error with Qdrant collection: {e}")
            logger.error(f"   Collection name: {self.collection_name}")
            logger.error(f"   Embedding dimension: {self.embedding_dimension}")
            # Re-raise to make the error visible
            raise

    async def add_documents(
        self,
        document_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Add document chunks to vector store

        Args:
            document_id: Database document ID
            chunks: List of text chunks
            embeddings: List of embedding vectors
            metadata: Optional metadata to attach to all chunks

        Returns:
            int: Number of chunks added
        """
        try:
            if len(chunks) != len(embeddings):
                raise ValueError("Number of chunks and embeddings must match")

            points = []
            base_metadata = metadata or {}

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
                point_metadata = {
                    **base_metadata,
                    "document_id": document_id,
                    "chunk_index": idx,
                    "chunk_text": chunk,
                }

                # 🔧 FIX: Generate UUID instead of using large integer IDs
                # Qdrant expects either UUID strings or small unsigned integers
                point_id = str(uuid.uuid4())

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=point_metadata,
                    )
                )

            # Batched upload using async client
            batch_size = 100
            for i in range(0, len(points), batch_size):
                await self.async_client.upsert(
                    collection_name=self.collection_name,
                    points=points[i : i + batch_size],
                )

            logger.info(f"Added {len(chunks)} chunks for document {document_id}")
            return len(chunks)
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    async def search(
        self,
        query_embedding: list[float],
        document_id: int | None = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Search for similar chunks using semantic search

        Args:
            query_embedding: Query vector
            document_id: Optional filter by document ID
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of matching chunks with metadata
        """
        try:
            # Build filter if document_id provided
            query_filter = None
            if document_id is not None:
                query_filter = Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )

            # Perform search
            results = await self.async_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Format results
            formatted_results = []
            for result in results.points:
                payload = result.payload or {}

                formatted_results.append(
                    {
                        "chunk_text": payload.get("chunk_text", ""),
                        "document_id": payload.get("document_id"),
                        "chunk_index": payload.get("chunk_index"),
                        "score": result.score,
                        "metadata": {
                            k: v
                            for k, v in payload.items()
                            if k not in ["chunk_text", "document_id", "chunk_index"]
                        },
                    }
                )

            logger.info(f"Found {len(formatted_results)} similar chunks")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            raise

    async def delete_document(self, document_id: int) -> bool:
        """
        Delete all chunks for a document

        Args:
            document_id: Database document ID

        Returns:
            bool: True if successful
        """
        try:
            await self.async_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {e}")
            return False

    async def get_document_chunks_count(self, document_id: int) -> int:
        """
        Get number of chunks for a document

        Args:
            document_id: Database document ID

        Returns:
            int: Number of chunks
        """
        try:
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

            result = await self.async_client.count(
                collection_name=self.collection_name,
                count_filter=filter_condition,
            )

            return result.count

        except Exception as e:
            logger.error(f"Error counting document chunks: {e}")
            raise
