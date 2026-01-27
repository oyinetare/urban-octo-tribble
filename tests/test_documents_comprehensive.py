from io import BytesIO

import pytest
from httpx import AsyncClient

from app.models import Document


class TestDocumentsComprehensive:
    """Comprehensive document tests for full coverage."""

    @pytest.mark.asyncio
    async def test_create_document_full(self, client: AsyncClient, auth_headers):
        # Create valid PDF content (small, under 10MB)
        file_content = b"%PDF-1.4\n%fake pdf content for testing"
        file_obj = BytesIO(file_content)

        files = {"file": ("test.pdf", file_obj, "application/pdf")}
        data = {"title": "Complete Document", "description": "Full description"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["title"] == "Complete Document"
        assert response_data["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_create_document_minimal(self, client: AsyncClient, auth_headers):
        """Test creating document with minimal fields."""
        file_content = b"%PDF-1.4\n%minimal pdf content"
        file_obj = BytesIO(file_content)

        files = {"file": ("minimal.pdf", file_obj, "application/pdf")}
        data = {"title": "Minimal Document", "description": "Minimal description"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, client: AsyncClient, auth_headers):
        """Test uploading file larger than 10MB limit."""
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        file_obj = BytesIO(large_content)

        files = {"file": ("large.pdf", file_obj, "application/pdf")}
        data = {"title": "Large Document", "description": "Too large"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Debug
        print(f"\nLARGE FILE TEST: Status={response.status_code}, Body={response.text}")

        # Should fail validation with 400 or 422
        assert response.status_code in [400, 422]

        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert any(word in message for word in ["large", "size", "max"])

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient, auth_headers):
        """Test uploading unsupported file type."""
        file_content = b"fake image content"
        file_obj = BytesIO(file_content)

        files = {"file": ("image.jpg", file_obj, "image/jpeg")}
        data = {"title": "Image Document", "description": "Should fail"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Debug
        print(f"\nINVALID TYPE TEST: Status={response.status_code}, Body={response.text}")

        # Should fail validation
        assert response.status_code in [400, 422]

        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert any(word in message for word in ["type", "invalid", "allowed"])

    @pytest.mark.asyncio
    async def test_upload_valid_text_file(self, client: AsyncClient, auth_headers):
        """Test uploading valid text file."""
        file_content = b"This is a text document with some content."
        file_obj = BytesIO(file_content)

        files = {"file": ("document.txt", file_obj, "text/plain")}
        data = {"title": "Text Document", "description": "Plain text"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_valid_docx_file(self, client: AsyncClient, auth_headers):
        """Test uploading valid DOCX file."""
        file_content = b"PK\x03\x04fake docx content"  # DOCX files start with PK
        file_obj = BytesIO(file_content)

        files = {
            "file": (
                "document.docx",
                file_obj,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {"title": "Word Document", "description": "DOCX file"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get_document_success(self, client: AsyncClient, auth_headers, test_document):
        """Test getting existing document."""
        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent document."""
        response = await client.get("/api/v1/documents/999999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_document_title_only(
        self, client: AsyncClient, auth_headers, test_document
    ):
        """Test updating only title."""
        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"title": "New Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_document_all_fields(
        self, client: AsyncClient, auth_headers, test_document
    ):
        """Test updating all fields."""
        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "description": "Updated Description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated Description"

    @pytest.mark.asyncio
    async def test_delete_document_success(self, client: AsyncClient, auth_headers, test_document):
        """Test deleting document."""
        response = await client.delete(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client: AsyncClient, session):
        """Test listing documents when user has none."""
        from app.core import token_manager
        from app.models import User

        # Create new user with no documents
        new_user = User(
            email="empty@test.com",
            username="emptyuser",
            hashed_password=token_manager.get_password_hash("password"),
            role="user",
        )
        session.add(new_user)
        await session.commit()

        token = token_manager.create_access_token(
            data={"sub": new_user.username, "scopes": ["read", "write"]}
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test document pagination."""
        # Create 25 documents
        for i in range(25):
            doc = Document(
                title=f"Doc {i}",
                description=f"Description {i}",
                owner_id=test_user.id,
                storage_key="temporary_key",
                filename="Test.pdf",
                file_size=1024,
                content_type="application/pdf",
                processing_status="pending",
            )
            session.add(doc)
        await session.commit()

        # Get first page
        response = await client.get("/api/v1/documents?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["total"] >= 25

    @pytest.mark.asyncio
    async def test_list_documents_search(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test searching documents."""
        # Create specific documents
        doc1 = Document(
            title="Python Tutorial",
            description="Learn Python programming",
            owner_id=test_user.id,
            storage_key="temporary_key",
            filename="Test.pdf",
            file_size=1024,
            content_type="application/pdf",
            processing_status="pending",
        )
        doc2 = Document(
            title="JavaScript Guide",
            description="Learn JavaScript",
            owner_id=test_user.id,
            storage_key="temporary_key",
            filename="Test.pdf",
            file_size=1024,
            content_type="application/pdf",
            processing_status="pending",
        )
        session.add_all([doc1, doc2])
        await session.commit()

        # Search for Python
        response = await client.get("/api/v1/documents?search=Python", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert any("Python" in item["title"] for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_documents_sort_asc(self, client: AsyncClient, auth_headers):
        """Test sorting documents ascending."""
        response = await client.get(
            "/api/v1/documents?sort_by=title&sort_order=asc", headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_documents_sort_desc(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test sorting documents descending."""
        response = await client.get(
            "/api/v1/documents?sort_by=created_at&sort_order=desc", headers=auth_headers
        )
        assert response.status_code == 200
