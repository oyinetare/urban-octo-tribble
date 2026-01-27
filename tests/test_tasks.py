import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import ProcessingStatus
from app.tasks.document_processing import _async_process, process_document


@pytest.mark.asyncio
class TestDocumentTasks:
    @pytest.fixture
    def mock_db_factory(self, session):
        """Unified factory for 'async with AsyncSessionLocal()' mocks."""
        factory = MagicMock()
        # Mocking the async context manager protocol (__aenter__ / __aexit__)
        factory.return_value.__aenter__ = AsyncMock(return_value=session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return factory

    async def test_extraction_pdf_success(self, session, test_document, mock_db_factory):
        """Test successful text extraction for a PDF."""
        mock_content = b"Mock PDF Content"
        mock_text = "Extracted PDF Text"

        with (
            patch(
                "app.tasks.document_processing.storage_service.download", new_callable=AsyncMock
            ) as mock_download,
            patch(
                "app.tasks.document_processing.extraction_factory.get_extractor"
            ) as mock_get_factory,
            patch("app.tasks.document_processing.AsyncSessionLocal", new=mock_db_factory),
        ):
            mock_download.return_value = mock_content
            mock_extractor = AsyncMock()
            mock_extractor.extract.return_value = mock_text
            mock_get_factory.return_value = mock_extractor

            # Execute - pass a mock task as 'self'
            result = await _async_process(MagicMock(), test_document.id)

            assert result["status"] == "success"

            # Refresh from DB via the shared session fixture
            await session.refresh(test_document)
            assert test_document.content == mock_text
            assert test_document.processing_status == ProcessingStatus.COMPLETED

    async def test_status_updates_progress(self, test_document, mock_db_factory):
        """Test that update_state is called with correct percentages."""
        mock_task = MagicMock()
        mock_task.update_state = MagicMock()

        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = "some text"

        with (
            patch("app.tasks.document_processing.storage_service.download", new_callable=AsyncMock),
            patch(
                "app.tasks.document_processing.extraction_factory.get_extractor",
                return_value=mock_extractor,
            ),
            patch("app.tasks.document_processing.AsyncSessionLocal", new=mock_db_factory),
        ):
            await _async_process(mock_task, test_document.id)

            # Verify specific progress steps
            mock_task.update_state.assert_any_call(
                state="PROGRESS", meta={"percent": 10, "step": "fetching"}
            )
            mock_task.update_state.assert_any_call(
                state="PROGRESS", meta={"percent": 40, "step": "downloading"}
            )

    async def test_on_failure_updates_db(self, session, test_document, mock_db_factory):
        """Test the Celery on_failure handler updates DB status to failed."""
        from app.tasks.document_processing import ProcessingTask

        task_handler = ProcessingTask()
        error_exc = Exception("MinIO Connection Timeout")

        # Bridge asyncio.run (from app) to the current test loop
        def mock_run_in_existing_loop(coro):
            return asyncio.get_event_loop().create_task(coro)

        with (
            patch("app.tasks.document_processing.AsyncSessionLocal", new=mock_db_factory),
            patch(
                "app.tasks.document_processing.asyncio.run", side_effect=mock_run_in_existing_loop
            ),
        ):
            # Call sync handler
            task_handler.on_failure(
                exc=error_exc, task_id="test-id", args=[test_document.id], kwargs={}, einfo=None
            )

            # Yield control to let the background task finish
            await asyncio.sleep(0.05)

            await session.refresh(test_document)
            assert test_document.processing_status == "failed"
            assert "MinIO Connection Timeout" in test_document.processing_error

    def test_retry_logic_configuration(self):
        """Verify the task is configured for retries (Synchronous)."""
        # Check retries
        assert process_document.max_retries == 3

        # In some Celery versions, 'bind' is a decorator-time setting
        # that doesn't stay as a public boolean.
        # You can check if the first argument of the task is 'self'
        # or check the task's actual class.
        from app.tasks.document_processing import ProcessingTask

        assert isinstance(process_document, ProcessingTask)
