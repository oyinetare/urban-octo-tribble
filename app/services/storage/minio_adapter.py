from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from unittest.mock import AsyncMock

import aioboto3
from botocore.exceptions import ClientError

from app.core import get_settings
from app.exceptions import StorageException
from app.utility import id_generator

settings = get_settings()


class StorageAdapter(ABC):
    @abstractmethod
    async def upload(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        user_id: int | None = None,
    ) -> str:
        pass

    @abstractmethod
    async def download(self, object_key: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, object_key: str) -> None:
        pass

    @abstractmethod
    async def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        pass

    @abstractmethod
    async def file_exists(self, object_key: str) -> bool:
        pass


class MockStorageAdapter(StorageAdapter):
    """Type-safe Mock implementation for tests."""

    def __init__(self):
        # Create internal mocks to track calls
        self._upload_mock = AsyncMock(return_value="uploads/test_key.pdf")
        self._download_mock = AsyncMock(return_value=b"test content")
        self._delete_mock = AsyncMock(return_value=None)
        self._presigned_url_mock = AsyncMock(return_value="http://test.com")
        self._file_exists_mock = AsyncMock(return_value=True)

    async def _ensure_bucket_exists(self):
        """Mock the internal initialization method called by services.init()"""
        return None

    async def upload(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        user_id: int | None = None,
    ) -> str:
        # Call the internal mock and return its result
        return await self._upload_mock(file_data, filename, content_type, user_id)

    async def download(self, object_key: str) -> bytes:
        return await self._download_mock(object_key)

    async def delete(self, object_key: str) -> None:
        await self._delete_mock(object_key)

    async def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        return await self._presigned_url_mock(object_key, expires)

    async def file_exists(self, object_key: str) -> bool:
        return await self._file_exists_mock(object_key)


class MinIOAdapter(StorageAdapter):
    """Service for managing file storage in MinIO using async patterns."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        use_ssl: bool = False,
    ):
        self.session = aioboto3.Session()
        # MinIO is S3-compatible, so we use the 's3' service identifier
        self.config = {
            "endpoint_url": f"{'https' if use_ssl else 'http'}://{endpoint}",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        self.bucket_name = bucket_name

    async def _ensure_bucket_exists(self):
        """Asynchronously check or create the bucket."""
        async with self.session.client("s3", **self.config) as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket_name)
            except ClientError:
                try:
                    await s3.create_bucket(Bucket=self.bucket_name)
                except ClientError as inner_e:
                    raise StorageException(f"Failed to create bucket: {inner_e}") from inner_e

    async def upload(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        user_id: int | None = None,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_data: File-like object containing the data
            filename: Original filename
            content_type: MIME type of the file
            user_id: Optional user ID for organizing files

        Returns:
            str: Object key (path) in MinIO

        Raises:
            StorageException: If upload fails
        """
        # Generate unique object key
        unique_id = str(id_generator.generate())

        suffix = Path(filename).suffix  # returns ".txt" (including the dot)
        unique_id = str(id_generator.generate())

        if user_id:
            object_key = f"users/{user_id}/{unique_id}{suffix}"
        else:
            object_key = f"uploads/{unique_id}{suffix}"

        async with self.session.client("s3", **self.config) as s3:
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file_data,
                    ContentType=content_type,
                )
                return object_key
            except ClientError as e:
                raise StorageException(f"Async upload failed: {e}") from e

    async def download(self, object_key: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_key: Object key (path) in MinIO

        Returns:
            bytes: File contents

        Raises:
            StorageException: If download fails
        """
        async with self.session.client("s3", **self.config) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket_name, Key=object_key)
                async with response["Body"] as stream:
                    return await stream.read()
            except ClientError as e:
                raise StorageException(f"Async download failed: {e}") from e

    async def delete(self, object_key: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_key: Object key (path) in MinIO

        Raises:
            StorageException: If deletion fails
        """
        async with self.session.client("s3", **self.config) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket_name, Key=object_key)
            except ClientError as e:
                raise StorageException(f"Async deletion failed: {e}") from e

    async def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate a presigned URL using the async client for temporary file access.

        Args:
            object_key: Object key (path) in MinIO
            expires: URL expiration time

        Returns:
            str: Presigned URL

        Raises:
            StorageException: If URL generation fails
        """
        async with self.session.client("s3", **self.config) as s3:
            try:
                return s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": object_key},
                    ExpiresIn=expires,
                )
            except ClientError as e:
                raise StorageException(f"Failed to generate URL: {e}") from e

    async def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_key: Object key (path) in MinIO

        Returns:
            bool: True if file exists, False otherwise
        """
        async with self.session.client("s3", **self.config) as s3:
            try:
                await s3.head_object(Bucket=self.bucket_name, Key=object_key)
                return True
            except ClientError:
                return False


storage_service = MinIOAdapter(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    bucket_name=settings.MINIO_DOCUMENTS_BUCKET_NAME,
    use_ssl=settings.MINIO_USE_SSL,
)
