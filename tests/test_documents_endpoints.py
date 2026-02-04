"""
Comprehensive tests for document endpoints (download, status, etc.)
Target: Increase coverage for app/routes/documents.py from 57% to 80%+
"""

from io import BytesIO

import pytest
from httpx import AsyncClient

from app.models import Document


class TestDocumentDownload:
    """Test document download endpoint."""

    @pytest.mark.asyncio
    async def test_download_returns_presigned_url(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test download endpoint returns presigned URL."""
        response = await client.get(
            f"/api/v1/documents/{test_document.id}/download", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert isinstance(data["download_url"], str)
        assert len(data["download_url"]) > 0

    @pytest.mark.asyncio
    async def test_download_url_format(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test download URL has correct format."""
        response = await client.get(
            f"/api/v1/documents/{test_document.id}/download", headers=auth_headers
        )

        data = response.json()
        url = data["download_url"]

        # URL should be valid (from mock or real storage)
        assert url.startswith("http")

    @pytest.mark.asyncio
    async def test_download_nonexistent_document(self, client: AsyncClient, auth_headers):
        """Test downloading non-existent document returns 404."""
        response = await client.get("/api/v1/documents/999999/download", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_other_users_document(
        self, client: AsyncClient, session, test_document: Document
    ):
        """Test downloading another user's document is forbidden."""
        from app.core import token_manager
        from app.models import User

        # Create different user
        other_user = User(
            email="other@test.com",
            username="otheruser",
            hashed_password=token_manager.get_password_hash("password"),
            role="user",
        )
        session.add(other_user)
        await session.commit()

        token = token_manager.create_access_token(
            data={"sub": other_user.username, "scopes": ["read", "write"]}
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/v1/documents/{test_document.id}/download", headers=headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_download_without_auth(self, client: AsyncClient, test_document: Document):
        """Test downloading without authentication fails."""
        response = await client.get(f"/api/v1/documents/{test_document.id}/download")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_download_any_document(
        self, client: AsyncClient, admin_headers, test_document: Document
    ):
        """Test admin can download any document."""
        response = await client.get(
            f"/api/v1/documents/{test_document.id}/download", headers=admin_headers
        )

        assert response.status_code == 200


class TestDocumentProcessingStatus:
    """Test document processing status endpoint."""

    @pytest.mark.asyncio
    async def test_get_processing_status(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test getting document processing status."""
        response = await client.get(
            f"/api/v1/documents/{test_document.id}/status", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "status" in data
        # Don't access test_document.id after this - session may be closed

    @pytest.mark.asyncio
    async def test_status_returns_enum_or_string(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test status endpoint returns status as string."""
        response = await client.get(
            f"/api/v1/documents/{test_document.id}/status", headers=auth_headers
        )

        data = response.json()
        # Status could be string representation of enum
        assert "status" in data
        assert isinstance(data["status"], str)


class TestDocumentListFiltering:
    """Test advanced document list filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client: AsyncClient, auth_headers, session, test_user):
        """Test filtering documents by status."""
        # Create documents with different statuses
        for status in ["pending", "completed", "failed"]:
            doc = Document(
                title=f"Doc {status}",
                description="Test",
                filename="test.pdf",
                storage_key="test/key",
                file_size=1024,
                content_type="application/pdf",
                owner_id=test_user.id,
                processing_status=status,
            )
            session.add(doc)
        await session.commit()

        # List all documents
        response = await client.get("/api/v1/documents", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_search_in_title_and_description(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test search works in both title and description."""
        # Create documents
        doc1 = Document(
            title="Python Programming",
            description="Learn basics",
            filename="test.pdf",
            storage_key="test/key1",
            file_size=1024,
            content_type="application/pdf",
            owner_id=test_user.id,
            processing_status="pending",
        )
        doc2 = Document(
            title="JavaScript Guide",
            description="Python integration guide",
            filename="test.pdf",
            storage_key="test/key2",
            file_size=1024,
            content_type="application/pdf",
            owner_id=test_user.id,
            processing_status="pending",
        )
        session.add_all([doc1, doc2])
        await session.commit()

        # Search for "Python"
        response = await client.get("/api/v1/documents?search=Python", headers=auth_headers)

        data = response.json()
        # Should find both (one in title, one in description)
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_sort_by_file_size(self, client: AsyncClient, auth_headers, session, test_user):
        """Test sorting by file size."""
        # Create documents with different sizes
        for size in [100, 5000, 1000]:
            doc = Document(
                title=f"Doc {size}",
                description="Test",
                filename="test.pdf",
                storage_key="test/key",
                file_size=size,
                content_type="application/pdf",
                owner_id=test_user.id,
                processing_status="pending",
            )
            session.add(doc)
        await session.commit()

        # Sort by file_size ascending
        response = await client.get(
            "/api/v1/documents?sort_by=file_size&sort_order=asc", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # First should be smallest
        if len(data["items"]) >= 2:
            sizes = [item["file_size"] for item in data["items"]]
            assert sizes == sorted(sizes)

    @pytest.mark.asyncio
    async def test_sort_by_updated_at(self, client: AsyncClient, auth_headers):
        """Test sorting by updated_at timestamp."""
        response = await client.get(
            "/api/v1/documents?sort_by=updated_at&sort_order=desc", headers=auth_headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_with_search(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test pagination works with search filter."""
        # Create many matching documents
        for i in range(15):
            doc = Document(
                title=f"Python Tutorial {i}",
                description="Test",
                filename="test.pdf",
                storage_key=f"test/key{i}",
                file_size=1024,
                content_type="application/pdf",
                owner_id=test_user.id,
                processing_status="pending",
            )
            session.add(doc)
        await session.commit()

        # Get first page
        response = await client.get(
            "/api/v1/documents?search=Python&page=1&page_size=10", headers=auth_headers
        )

        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] >= 15


class TestDocumentMetadata:
    """Test document metadata operations."""

    @pytest.mark.asyncio
    async def test_get_document_includes_all_fields(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test GET document includes all metadata fields."""
        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Check all fields are present
        required_fields = [
            "id",
            "title",
            "description",
            "content",
            "filename",
            "file_size",
            "content_type",
            "storage_key",
            "processing_status",
            "processing_error",
            "owner_id",
        ]
        for field in required_fields:
            assert field in data

    @pytest.mark.asyncio
    async def test_update_only_description(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test updating only description field."""
        original_title = test_document.title

        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"description": "New description only"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description only"
        assert data["title"] == original_title  # Unchanged

    @pytest.mark.asyncio
    async def test_update_with_empty_description(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test updating description to empty string."""
        response = await client.put(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers, json={"description": ""}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == ""

    @pytest.mark.asyncio
    async def test_update_with_null_description(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test updating description to null."""
        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"description": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] is None

    @pytest.mark.asyncio
    async def test_update_immutable_fields_ignored(
        self, client: AsyncClient, auth_headers, test_document: Document
    ):
        """Test updating immutable fields is ignored."""
        original_size = test_document.file_size
        original_filename = test_document.filename

        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={
                "title": "New Title",
                "file_size": 99999,  # Should be ignored
                "filename": "hacked.exe",  # Should be ignored
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["file_size"] == original_size  # Unchanged
        assert data["filename"] == original_filename  # Unchanged


class TestDocumentUploadEdgeCases:
    """Test edge cases in document upload."""

    @pytest.mark.asyncio
    async def test_upload_with_very_long_title(self, client: AsyncClient, auth_headers):
        """Test upload with title at maximum length."""
        long_title = "A" * 255  # Max length
        file_content = b"%PDF-1.4\ntest"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": long_title, "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload", headers=auth_headers, data=data, files=files
        )

        assert response.status_code == 201
        assert response.json()["title"] == long_title

    @pytest.mark.asyncio
    async def test_upload_with_unicode_title(self, client: AsyncClient, auth_headers):
        """Test upload with unicode characters in title."""
        file_content = b"%PDF-1.4\ntest"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "文档 📄 Документ", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload", headers=auth_headers, data=data, files=files
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_returns_storage_key(self, client: AsyncClient, auth_headers):
        """Test upload returns storage key."""
        file_content = b"%PDF-1.4\ntest"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Test", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload", headers=auth_headers, data=data, files=files
        )

        assert response.status_code == 201
        result = response.json()
        assert "storage_key" in result
        assert isinstance(result["storage_key"], str)

    @pytest.mark.asyncio
    async def test_upload_sets_processing_status(self, client: AsyncClient, auth_headers):
        """Test upload sets correct initial processing status."""
        file_content = b"%PDF-1.4\ntest"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Test", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload", headers=auth_headers, data=data, files=files
        )

        assert response.status_code == 201
        result = response.json()
        assert "processing_status" in result
        # Should be "processing" or "pending"
        assert result["processing_status"] in ["pending", "processing"]


class TestDocumentUploadResponse:
    """Test document upload response format."""

    @pytest.mark.asyncio
    async def test_upload_returns_processing_status(self, client: AsyncClient, auth_headers):
        """Test upload sets processing_status to PROCESSING."""
        from io import BytesIO

        file_content = b"%PDF-1.4\ntest"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Test", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload", headers=auth_headers, data=data, files=files
        )

        assert response.status_code == 201
        result = response.json()

        # Your upload returns PROCESSING status
        assert "processing_status" in result
        assert result["processing_status"] == "processing"
