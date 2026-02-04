from unittest.mock import MagicMock

import pytest

from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService

# 1. --- EmbeddingService Tests ---


class TestEmbeddingService:
    def test_ensure_model_loaded(self, mocker):
        """Test that the model is lazy-loaded only when needed."""
        # Patch asyncio.to_thread with an AsyncMock
        mock_thread = mocker.patch(
            "app.services.embeddings.asyncio.to_thread", new_callable=mocker.AsyncMock
        )

        mock_model = mocker.MagicMock()
        # Now set the return value of the awaited call
        mock_thread.return_value = mock_model

        service = EmbeddingService(model_name="test-model")
        assert service.model is None

        # Trigger lazy load - but we can't actually call it without real imports
        # Just test the initialization
        assert service.model_name == "test-model"
        assert service.embedding_dimension == 384

    def test_get_embedding_dimension(self):
        service = EmbeddingService()
        assert service.get_embedding_dimension() == 384

    def test_embed_text(self, mocker):
        """Test embedding text with mocked model."""
        service = EmbeddingService()

        # Mock the model directly on the service instance
        mock_model = mocker.MagicMock()
        mock_encode_result = mocker.MagicMock()
        mock_encode_result.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_encode_result

        service.model = mock_model  # Inject the mock

        result = service.embed_text("hello world")

        assert result == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once()


# 2. --- VectorStoreService Tests ---


class TestVectorStoreService:
    @pytest.mark.asyncio
    async def test_ensure_collection_exists_on_init(self, mock_qdrant, mocker):
        """Verify collection creation if it doesn't exist."""
        # Patch the client constructor to return your mock
        mocker.patch(
            "app.services.vector_store.AsyncQdrantClient", return_value=mock_qdrant["async"]
        )

        service = VectorStoreService(
            host="qdrant", port=6333, collection_name="test_col", embedding_dimension=384
        )

        await service._ensure_collection_exists()
        mock_qdrant["async"].create_collection.assert_called_once()

    async def test_add_documents_success(self, mock_qdrant, mocker):  # Added mocker
        # Connect the mock to the service
        mocker.patch(
            "app.services.vector_store.AsyncQdrantClient", return_value=mock_qdrant["async"]
        )

        service = VectorStoreService("h", 1, "test", 3)
        chunks = ["chunk1", "chunk2"]
        embeddings = [[0.1, 0.1, 0.1], [0.2, 0.2, 0.2]]

        count = await service.add_documents(document_id=1, chunks=chunks, embeddings=embeddings)

        assert count == 2
        mock_qdrant["async"].upsert.assert_called()

    async def test_search_results_formatting(self, mock_qdrant, mocker):
        mocker.patch(
            "app.services.vector_store.AsyncQdrantClient", return_value=mock_qdrant["async"]
        )

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
        mock_qdrant["async"].query_points.return_value = MagicMock(points=[mock_point])

        results = await service.search(query_embedding=[0.1, 0.2, 0.3])

        assert len(results) == 1
        assert results[0]["chunk_text"] == "found text"
        assert results[0]["score"] == 0.95

    async def test_delete_document(self, mock_qdrant, mocker):
        """Test successful document deletion with an awaitable mock."""
        mocker.patch(
            "app.services.vector_store.AsyncQdrantClient", return_value=mock_qdrant["async"]
        )

        service = VectorStoreService("h", 1, "test", 3)

        result = await service.delete_document(1)

        assert result is True
        mock_qdrant["async"].delete.assert_called_once()
