from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import ProcessingStatus
from app.tasks.document_processing import _async_process


@pytest.mark.asyncio
class TestDocumentTasks:
    @pytest.fixture
    def mock_db_factory(self, session):
        """Creates a mock factory for 'async with AsyncSessionLocal()'"""
        factory = MagicMock()
        # This makes the mock act like an async context manager returning your session
        factory.return_value.__aenter__ = AsyncMock(return_value=session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        return factory

    # 1. Update the session patch to handle context management
    @pytest.fixture
    def mock_session_factory(self, session):
        """Returns a factory that acts as an async context manager."""
        mock_factory = MagicMock()
        # This allows: async with AsyncSessionLocal() as session:
        mock_factory.return_value.__aenter__.return_value = session
        return mock_factory

    async def test_extraction_pdf_success(self, session, test_document, mock_db_factory):
        mock_content = b"Mock PDF Content"
        mock_text = "Extracted PDF Text"

        with (
            patch(
                "app.tasks.document_processing.storage_service.download", new_callable=AsyncMock
            ) as mock_download,
            patch(
                "app.tasks.document_processing.extraction_factory.get_extractor"
            ) as mock_get_factory,
            # Patch the class/factory, not the instance
            patch("app.tasks.document_processing.AsyncSessionLocal", new=mock_db_factory),
        ):
            mock_download.return_value = mock_content
            mock_extractor = AsyncMock()
            mock_extractor.extract.return_value = mock_text
            mock_get_factory.return_value = mock_extractor

            # Execute
            # result = await _async_process(test_document.id)
            result = await _async_process(MagicMock(), test_document.id)

            # Assert
            assert result["status"] == "success"
            # Refresh ensures we see changes from the transaction inside _async_process
            await session.refresh(test_document)
            assert test_document.content == mock_text
            assert test_document.processing_status == ProcessingStatus.COMPLETED

    async def test_status_updates_progress(self, test_document, mock_session_factory):
        mock_task = MagicMock()
        mock_task.update_state = MagicMock()

        # Create an AsyncMock for the extractor so it can be awaited
        mock_extractor = AsyncMock()
        mock_extractor.extract.return_value = "some text"

        with (
            patch("app.tasks.document_processing.storage_service.download", new_callable=AsyncMock),
            # Configure the factory to return our AsyncMock extractor
            patch(
                "app.tasks.document_processing.extraction_factory.get_extractor",
                return_value=mock_extractor,
            ),
            patch("app.tasks.document_processing.AsyncSessionLocal", new=mock_session_factory),
        ):
            # Now 'await extractor.extract(content)' will work
            await _async_process(mock_task, test_document.id)

            # Verify progress calls
            mock_task.update_state.assert_any_call(
                state="PROGRESS", meta={"percent": 10, "step": "fetching"}
            )
            mock_task.update_state.assert_any_call(
                state="PROGRESS", meta={"percent": 40, "step": "downloading"}
            )

    async def test_on_failure_updates_db(self, session, test_document, mock_session_factory):
        import asyncio

        from app.tasks.document_processing import ProcessingTask

        task_handler = ProcessingTask()
        error_exc = Exception("MinIO Connection Timeout")

        # 1. Mock run to execute the coroutine in the EXISTING loop
        def mock_run_in_existing_loop(coro):
            return asyncio.get_event_loop().create_task(coro)

        with (
            patch("app.tasks.document_processing.AsyncSessionLocal", new=mock_session_factory),
            patch(
                "app.tasks.document_processing.asyncio.run", side_effect=mock_run_in_existing_loop
            ),
        ):
            # 2. This starts the async task in the background
            task_handler.on_failure(
                exc=error_exc, task_id="test-id", args=[test_document.id], kwargs={}, einfo=None
            )

            # 3. CRITICAL: Wait a tiny bit for the background task to finish
            await asyncio.sleep(0.1)

            # 4. Refresh and Assert
            await session.refresh(test_document)
            assert test_document.processing_status == "failed"
            assert "MinIO Connection Timeout" in test_document.processing_error
