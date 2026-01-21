import uuid
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.exceptions import StorageException

settings = get_settings()


class StorageService:
    """Service for managing file storage in MinIO/S3."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        use_ssl: bool = False,
    ):
        """Initialize MinIO client."""
        self.client = Minio(endpoint, access_key, secret_key, secure=use_ssl)
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise StorageException(f"Failed to create bucket: {str(e)}") from e

    def upload_file(
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
        file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        unique_id = str(uuid.uuid4())

        if user_id:
            object_key = f"users/{user_id}/{unique_id}.{file_ext}"
        else:
            object_key = f"uploads/{unique_id}.{file_ext}"

        try:
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=file_data,
                length=file_size,
                content_type=content_type,
            )

            return object_key

        except S3Error as e:
            raise StorageException(f"Failed to upload file: {str(e)}") from e

    def download_file(self, object_key: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_key: Object key (path) in MinIO

        Returns:
            bytes: File contents

        Raises:
            StorageException: If download fails
        """
        try:
            response = self.client.get_object(self.bucket_name, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data

        except S3Error as e:
            raise StorageException(f"Failed to download file: {str(e)}") from e

    def delete_file(self, object_key: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_key: Object key (path) in MinIO

        Raises:
            StorageException: If deletion fails
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
        except S3Error as e:
            raise StorageException(f"Failed to delete file: {str(e)}") from e

    def get_presigned_url(self, object_key: str, expires: timedelta = timedelta(hours=1)) -> str:
        """
        Generate a presigned URL for temporary file access.

        Args:
            object_key: Object key (path) in MinIO
            expires: URL expiration time

        Returns:
            str: Presigned URL

        Raises:
            StorageException: If URL generation fails
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name, object_name=object_key, expires=expires
            )
            return url
        except S3Error as e:
            raise StorageException(f"Failed to generate presigned URL: {str(e)}") from e

    def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_key: Object key (path) in MinIO

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False
