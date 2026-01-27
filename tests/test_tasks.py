from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import ProcessingStatus
from app.tasks.document_processing import _async_process, process_document


@pytest.mark.asyncio
class TestDocumentTasks:
    """Tests for Celery document processing tasks."""

    async def test_extraction_pdf_success(self, session, test_document):
        """Test successful text extraction for a PDF."""
        # 1. Setup mocks
        mock_content = b"Mock PDF Content"
        mock_text = "Extracted PDF Text"

        # Mock storage download
        with (
            patch(
                "app.tasks.document_processing.storage_service.download", new_callable=AsyncMock
            ) as mock_download,
            patch(
                "app.tasks.document_processing.extraction_factory.get_extractor"
            ) as mock_get_factory,
        ):
            mock_download.return_value = mock_content

            # Mock the extractor behavior
            mock_extractor = AsyncMock()
            mock_extractor.extract.return_value = mock_text
            mock_get_factory.return_value = mock_extractor

            # 2. Run the async internal task logic
            # We use the session-based logic directly for testing
            with patch("app.tasks.document_processing.AsyncSessionLocal", return_value=session):
                result = await _async_process(test_document.id)

            # 3. Assertions
            assert result["status"] == "success"

            # Refresh from DB to verify persistence
            await session.refresh(test_document)
            assert test_document.content == mock_text
            assert test_document.processing_status == ProcessingStatus.COMPLETED
            assert test_document.processing_error is None

    async def test_extraction_unsupported_type(self, session, test_document):
        """Test error handling when no extractor exists for mime type."""
        with (
            patch(
                "app.tasks.document_processing.storage_service.download", new_callable=AsyncMock
            ) as mock_download,
            patch(
                "app.tasks.document_processing.extraction_factory.get_extractor"
            ) as mock_get_factory,
            patch("app.tasks.document_processing.AsyncSessionLocal", return_value=session),
        ):
            mock_download.return_value = b"some data"
            mock_get_factory.side_effect = ValueError("No extractor for mime type")

            with pytest.raises(ValueError, match="No extractor for mime type"):
                await _async_process(test_document.id)

    async def test_status_updates_progress(self, session, test_document):
        """Test that update_state is called with correct percentages."""
        mock_task = MagicMock()  # The 'self' in process_document(self, id)

        with (
            patch("app.tasks.document_processing.storage_service.download", new_callable=AsyncMock),
            patch("app.tasks.document_processing.extraction_factory.get_extractor"),
            patch("app.tasks.document_processing.AsyncSessionLocal", return_value=session),
        ):
            # We need to test the logic that calls self.update_state
            # So we call _async_process(self, document_id)
            from app.tasks.document_processing import _async_process as async_task_logic

            await async_task_logic(mock_task, test_document.id)

            # Verify progress calls
            # Check for specific steps defined in your task
            mock_task.update_state.assert_any_call(
                state="PROGRESS", meta={"percent": 10, "step": "fetching"}
            )
            mock_task.update_state.assert_any_call(
                state="PROGRESS", meta={"percent": 40, "step": "downloading"}
            )

    async def test_on_failure_updates_db(self, session, test_document):
        """Test the Celery on_failure handler updates DB status to failed."""
        from app.tasks.document_processing import ProcessingTask

        task_handler = ProcessingTask()
        error_exc = Exception("MinIO Connection Timeout")

        # Patch the Session factory to use our test session
        with patch("app.tasks.document_processing.AsyncSessionLocal", return_value=session):
            # args[0] is the document_id
            task_handler.on_failure(
                exc=error_exc, task_id="test-id", args=[test_document.id], kwargs={}, einfo=None
            )

            # Refresh DB
            await session.refresh(test_document)
            assert test_document.processing_status == ProcessingStatus.FAILED
            assert "MinIO Connection Timeout" in test_document.processing_error

    def test_retry_logic_configuration(self):
        """Verify the task is configured for retries."""

        # Check celery decorator attributes
        assert process_document.max_retries == 3
        assert process_document.bind is True
