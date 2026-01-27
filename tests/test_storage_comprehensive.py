from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from botocore.exceptions import ClientError

from app.exceptions import StorageException
from app.services.storage import MinIOAdapter, MockStorageAdapter


class TestMockStorageAdapter:
    """Tests for the Mock implementation to ensure it satisfies the interface."""

    @pytest.mark.asyncio
    async def test_mock_flow(self):
        adapter = MockStorageAdapter()
        assert await adapter.upload(BytesIO(b"data"), "test.txt") == "uploads/test_key.pdf"
        assert await adapter.download("key") == b"test content"
        assert await adapter.get_presigned_url("key") == "http://test.com"
        assert await adapter.file_exists("key") is True


class TestMinIOAdapter:
    """Comprehensive tests for MinIOAdapter using aioboto3."""

    @pytest_asyncio.fixture
    async def adapter(self):
        return MinIOAdapter(
            endpoint="localhost:9000",
            access_key="user",
            secret_key="pass",
            bucket_name="test-bucket",
        )

    @pytest_asyncio.fixture
    async def mock_s3(self):
        """Helper to mock the aioboto3 client context manager."""
        with patch("aioboto3.Session.client") as mock_client_ctx:
            mock_client = AsyncMock()
            # This handles: async with session.client() as s3:
            mock_client_ctx.return_value.__aenter__.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_upload_success(self, adapter, mock_s3):
        file_data = BytesIO(b"hello world")

        result = await adapter.upload(file_data, "hello.txt", user_id=42)

        assert "users/42/" in result
        assert result.endswith(".txt")
        mock_s3.put_object.assert_called_once()
        kwargs = mock_s3.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["ContentType"] == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_download_success(self, adapter, mock_s3):
        # S3 Body is an async context manager
        mock_body = AsyncMock()
        mock_body.read.return_value = b"file bytes"
        mock_body.__aenter__.return_value = mock_body

        mock_s3.get_object.return_value = {"Body": mock_body}

        result = await adapter.download("some/path.pdf")

        assert result == b"file bytes"
        mock_s3.get_object.assert_called_with(Bucket="test-bucket", Key="some/path.pdf")

    @pytest.mark.asyncio
    async def test_delete_success(self, adapter, mock_s3):
        await adapter.delete("targets/file.zip")
        mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="targets/file.zip")

    @pytest.mark.asyncio
    async def test_get_presigned_url_success(self, adapter, mock_s3):
        # CRITICAL: generate_presigned_url is SYNCHRONOUS in aioboto3
        mock_s3.generate_presigned_url = MagicMock(return_value="https://signed.link")

        url = await adapter.get_presigned_url("secret.pdf", expires=60)

        assert url == "https://signed.link"
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object", Params={"Bucket": "test-bucket", "Key": "secret.pdf"}, ExpiresIn=60
        )

    @pytest.mark.asyncio
    async def test_file_exists_variants(self, adapter, mock_s3):
        # Case 1: Exists
        mock_s3.head_object.return_value = {}
        assert await adapter.file_exists("yes.txt") is True

        # Case 2: Does not exist (raises ClientError)
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )
        assert await adapter.file_exists("no.txt") is False

    @pytest.mark.asyncio
    async def test_ensure_bucket_exists_logic(self, adapter, mock_s3):
        # Simulate bucket missing then being created
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
        )

        await adapter._ensure_bucket_exists()

        mock_s3.head_bucket.assert_called_once()
        mock_s3.create_bucket.assert_called_once_with(Bucket="test-bucket")

    @pytest.mark.asyncio
    async def test_upload_exception_handling(self, adapter, mock_s3):
        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal Error"}}, "PutObject"
        )

        with pytest.raises(StorageException) as exc:
            await adapter.upload(BytesIO(b"data"), "fail.txt")
        assert "Async upload failed" in str(exc.value)
