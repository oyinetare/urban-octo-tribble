from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import services
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService

# 1. --- EmbeddingService Tests ---


class TestEmbeddingService:
    def test_ensure_model_loaded(self, mocker):
        """Test that the model is lazy-loaded only when needed."""
        # Setup the mock using the mocker fixture
        mock_transformer = mocker.patch("sentence_transformers.SentenceTransformer")

        service = EmbeddingService(model_name="test-model")
        assert service.model is None

        # Trigger lazy load
        service._ensure_model_loaded()

        assert service.model is not None
        mock_transformer.assert_called_once_with("test-model")

    def test_get_embedding_dimension(self):
        service = EmbeddingService()
        assert service.get_embedding_dimension() == 384

    def test_embed_text(self, mocker):
        # Setup mock
        mock_transformer = mocker.patch("sentence_transformers.SentenceTransformer")
        mock_model = mock_transformer.return_value
        # Mocking tolist() behavior
        mock_model.encode.return_value = mocker.Mock()
        mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]

        service = EmbeddingService()
        result = service.embed_text("hello world")

        assert result == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once()


# 2. --- VectorStoreService Tests ---


@pytest.mark.asyncio
class TestVectorStoreService:
    @pytest.fixture
    def mock_qdrant(self):
        """Patch QdrantClient and AsyncQdrantClient to avoid network calls."""
        with (
            patch("app.services.vector_store.QdrantClient") as mock_sync,
            patch("app.services.vector_store.AsyncQdrantClient") as mock_async,
        ):
            # Setup sync client for __init__ collection check
            sync_instance = mock_sync.return_value
            sync_instance.get_collections.return_value = MagicMock(collections=[])

            async_instance = mock_async.return_value

            yield {"sync": sync_instance, "async": async_instance}

    async def test_ensure_collection_exists_on_init(self, mock_qdrant):
        """Verify collection creation if it doesn't exist."""
        VectorStoreService(
            host="localhost", port=6333, collection_name="test_col", embedding_dimension=384
        )

        mock_qdrant["sync"].create_collection.assert_called_once()
        args, kwargs = mock_qdrant["sync"].create_collection.call_args
        assert kwargs["collection_name"] == "test_col"

    async def test_add_documents_success(self, mock_qdrant):
        service = VectorStoreService("h", 1, "test", 3)
        mock_qdrant["async"].upsert = AsyncMock()

        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]

        count = await service.add_documents(document_id=1, chunks=chunks, embeddings=embeddings)

        assert count == 2
        mock_qdrant["async"].upsert.assert_called_once()

    @pytest.mark.usefixtures("mock_qdrant")  # Injects the fixture implicitly
    async def test_add_documents_mismatch_error(self):
        service = VectorStoreService("h", 1, "test", 3)
        with pytest.raises(ValueError, match="match"):
            await service.add_documents(1, ["one"], [[0.1], [0.2]])

    async def test_search_results_formatting(self, mock_qdrant):
        service = VectorStoreService("h", 1, "test", 3)

        # Setup mock search return
        mock_point = MagicMock()
        mock_point.id = "uuid"
        mock_point.score = 0.95
        mock_point.payload = {
            "chunk_text": "found text",
            "document_id": 1,
            "chunk_index": 0,
            "extra": "metadata",
        }

        # Mock the new Query API in Qdrant
        mock_qdrant["async"].query_points = AsyncMock(return_value=MagicMock(points=[mock_point]))

        results = await service.search(query_embedding=[0.1, 0.2, 0.3])

        assert len(results) == 1
        assert results[0]["chunk_text"] == "found text"
        assert results[0]["score"] == 0.95
        assert results[0]["metadata"]["extra"] == "metadata"

    @pytest.mark.asyncio
    async def test_delete_document(self, mocker):
        # If you are patching the async_client methods:
        mock_delete = mocker.patch.object(
            services.vector_store.async_client,
            "delete",
            new_callable=AsyncMock,  # CRITICAL: This makes it awaitable
        )
        mock_delete.return_value = AsyncMock()  # or the expected response object

        result = await services.vector_store.delete_document(1)
        assert result is True
        mock_delete.assert_called_once()
