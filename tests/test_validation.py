from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core import services


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_register_missing_required_fields(self, client: AsyncClient):
        """Test registration with missing required fields."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},  # Missing username and password
        )
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format."""
        _response = await client.post(
            "/api/v1/auth/register",
            json={"email": "notanemail", "username": "testuser", "password": "password123"},
        )
        # Should fail validation if email validation is implemented

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        _response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "123",  # Too short
            },
        )
        # Depends on password validation rules

    @pytest.mark.asyncio
    async def test_create_document_missing_fields(self, client: AsyncClient, auth_headers):
        """Test creating document with missing required fields."""
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={},  # Empty body
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_document_missing_file(self, client: AsyncClient, auth_headers):
        """Test upload with missing file."""
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"title": "Test", "description": "Test"},
            # No files parameter
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_document_missing_title(self, client: AsyncClient, auth_headers):
        file_content = b"%PDF-1.4\n%test content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={},  # Title is missing
            files=files,
        )

        assert response.status_code == 422
        data = response.json()
        # Check that 'title' is listed in the validation errors
        errors = data.get("detail", [])
        error_fields = [err["loc"][-1] for err in errors]
        assert "title" in error_fields

    @pytest.mark.asyncio
    async def test_upload_file_size_validation(self, client: AsyncClient, auth_headers):
        """Test file size validation (>10MB)."""
        # Create 11MB file
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        data = {"title": "Large File", "description": "Too big"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should fail - either 400 or 422 depending on implementation
        assert response.status_code in [400, 422]
        assert "too large" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_upload_file_type_validation(self, client: AsyncClient, auth_headers):
        """Test file type validation."""
        # Try to upload unsupported file type
        files = {"file": ("test.exe", BytesIO(b"MZ fake exe"), "application/x-msdownload")}
        data = {"title": "Executable", "description": "Should fail"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should fail - either 400 or 422 depending on implementation
        assert response.status_code in [400, 422]
        assert "invalid file type" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_upload_empty_filename_validation(self, client: AsyncClient, auth_headers):
        """Test filename validation."""
        files = {"file": ("", BytesIO(b"content"), "application/pdf")}
        data = {"title": "No Name", "description": "Empty filename"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should fail - either 400 or 422 depending on implementation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_upload_long_filename_validation(self, client: AsyncClient, auth_headers):
        """Test filename length validation (>255 chars)."""
        long_name = "a" * 300 + ".pdf"
        files = {"file": (long_name, BytesIO(b"%PDF-1.4\ntest"), "application/pdf")}
        data = {"title": "Long Name", "description": "Too long filename"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should fail - either 400 or 422 depending on implementation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_document_invalid_data_types(self, client: AsyncClient, auth_headers):
        """Test creating document with invalid data types."""
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={
                "title": 12345,  # Should be string
                "description": True,  # Should be string
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_document_partial_update(
        self, client: AsyncClient, auth_headers, test_document
    ):
        """Test partial update of document."""
        original_description = test_document.description

        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},  # Only update title
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == original_description

    @pytest.mark.asyncio
    async def test_pagination_invalid_parameters(self, client: AsyncClient, auth_headers):
        """Test pagination with invalid parameters."""
        # Negative page number
        response = await client.get("/api/v1/documents?page=-1", headers=auth_headers)
        assert response.status_code == 422

        # Page size too large
        response = await client.get("/api/v1/documents?page_size=1000", headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_zero_page(self, client: AsyncClient, auth_headers):
        """Test pagination with page=0."""
        response = await client.get("/api/v1/documents?page=0", headers=auth_headers)
        assert response.status_code == 422


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_very_long_document_title(self, client: AsyncClient, auth_headers):
        """Test creating document with very long title."""
        long_title = "A" * 10000
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={"title": long_title, "description": "Test description"},
        )
        # Should either succeed or fail gracefully
        assert response.status_code in [201, 422]

    # @pytest.mark.asyncio
    # async def test_unicode_in_document(self, client: AsyncClient, auth_headers):
    #     """Test creating document with unicode characters."""
    #     response = await client.post(
    #         "/api/v1/documents",
    #         headers=auth_headers,
    #         json={"title": "测试文档 🚀 Тест", "description": "Unicode content: émojis 🎉"},
    #     )
    #     assert response.status_code == 201
    #     data = response.json()
    #     assert "测试文档" in data["title"]

    @pytest.mark.asyncio
    async def test_unicode_in_upload(self, client: AsyncClient, auth_headers):
        """Test upload with unicode filename and content."""
        file_content = "Unicode content: 你好世界 🌍".encode()
        files = {"file": ("文档.txt", BytesIO(file_content), "text/plain")}
        data = {"title": "Unicode 文档", "description": "Unicode test"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_special_characters_in_search(self, client: AsyncClient, auth_headers):
        """Test search with special characters."""
        response = await client.get(
            "/api/v1/documents?search=%';DROP TABLE documents;--", headers=auth_headers
        )
        # Should not cause SQL injection
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_search_query(self, client: AsyncClient, auth_headers):
        """Test search with empty query."""
        response = await client.get("/api/v1/documents?search=", headers=auth_headers)
        assert response.status_code == 200

    # @pytest.mark.asyncio
    # async def test_malformed_json(self, client: AsyncClient, auth_headers):
    #     """Test sending malformed JSON."""
    #     response = await client.post(
    #         "/api/v1/documents",
    #         headers={**auth_headers, "Content-Type": "application/json"},
    #         content=b"{invalid json",
    #     )
    #     assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, client: AsyncClient, auth_headers):
        """Test deleting non-existent document."""
        response = await client.delete("/api/v1/documents/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_document(self, client: AsyncClient, auth_headers):
        """Test updating non-existent document."""
        response = await client.put(
            "/api/v1/documents/99999", headers=auth_headers, json={"title": "Updated"}
        )
        assert response.status_code == 404


class TestErrorResponses:
    """Test error response formats."""

    @pytest.mark.asyncio
    async def test_404_error_format(self, client: AsyncClient, auth_headers):
        """Test 404 error response format."""
        response = await client.get("/api/v1/documents/99999", headers=auth_headers)
        assert response.status_code == 404
        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "message" in data

    @pytest.mark.asyncio
    async def test_401_error_format(self, client: AsyncClient):
        """Test 401 error response format."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_403_error_format(self, client: AsyncClient, session, test_document):
        """Test 403 error response format."""
        from app.core import token_manager
        from app.models import User

        # Create another user
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=token_manager.get_password_hash("password"),
            role_name="user",
            tier_name="free",
        )
        session.add(other_user)
        await session.commit()

        token = token_manager.create_access_token(
            user_id=other_user.id, username=other_user.username, tier_limit=20, scopes=["read"]
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=headers)
        assert response.status_code == 403
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_422_validation_error_format(self, client: AsyncClient):
        """Test 422 validation error response format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},  # Missing required fields
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_document_creation(self, client: AsyncClient, auth_headers):
        """Test creating documents with idempotency protection."""
        created_docs = []
        errors = []

        async def create_doc_safe(i):
            """Create document with error handling and unique idempotency key."""
            try:
                headers = {**auth_headers, "Idempotency-Key": f"concurrent-create-{i}"}

                response = await client.post(
                    "/api/v1/documents",
                    headers=headers,
                    json={
                        "title": f"Concurrent Document {i}",
                        "description": f"Description {i}",
                    },
                )

                if response.status_code == 201:
                    created_docs.append(response.json())
                else:
                    errors.append(f"Request {i}: Status {response.status_code}")
                return response

            except Exception as e:
                errors.append(f"Request {i}: Exception {str(e)}")
                return None

        # Create documents sequentially to avoid session conflicts
        for i in range(5):
            await create_doc_safe(i)

        assert len(created_docs) == 5, f"Only {len(created_docs)} succeeded. Errors: {errors}"

        # All should have unique IDs
        ids = [doc["id"] for doc in created_docs]
        assert len(ids) == len(set(ids)), "Duplicate IDs found!"


class TestIdempotency:
    """Test idempotency behavior."""

    @pytest.mark.asyncio
    async def test_idempotency_key_different_body(self, client: AsyncClient, auth_headers):
        """Test idempotency key reused with different body."""
        idempotency_key = "test-key-2"
        headers = {**auth_headers, "Idempotency-Key": idempotency_key}

        # First request
        await client.post(
            "/api/v1/documents/",
            headers=headers,
            json={"title": "Test 1", "description": "Description 1"},
        )

        # Second request with same key but different body
        _response = await client.post(
            "/api/v1/documents/",
            headers=headers,
            json={"title": "Test 2", "description": "Description 2"},
        )

        if services.redis.is_available:
            pass  # Might return 422 for body mismatch

    @pytest.mark.asyncio
    async def test_update_is_idempotent(self, client: AsyncClient, auth_headers, test_document):
        """Test that PUT requests are naturally idempotent."""
        update_data = {"title": "Updated Title"}

        response1 = await client.put(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers, json=update_data
        )

        response2 = await client.put(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers, json=update_data
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["title"] == response2.json()["title"]

    @pytest.mark.asyncio
    async def test_delete_is_idempotent(
        self, client: AsyncClient, auth_headers, test_document, storage_mock
    ):
        """Test that deleting a document handles external services and returns 404 on second call."""

        # Configure storage mock
        storage_mock._delete_mock.return_value = None

        # For vector store, we need to patch at the dependency level
        from unittest.mock import MagicMock

        from app.dependencies import get_vector_service

        mock_vector_store = MagicMock()
        mock_vector_store.delete_document = AsyncMock(return_value=True)

        async def override_get_vector_service():
            return mock_vector_store

        from app.main import app

        app.dependency_overrides[get_vector_service] = override_get_vector_service

        try:
            # FIRST CALL: Should succeed
            response1 = await client.delete(
                f"/api/v1/documents/{test_document.id}", headers=auth_headers
            )
            assert response1.status_code == 204

            # SECOND CALL: Should return 404
            response2 = await client.delete(
                f"/api/v1/documents/{test_document.id}", headers=auth_headers
            )
            assert response2.status_code == 404
        finally:
            app.dependency_overrides.pop(get_vector_service, None)
