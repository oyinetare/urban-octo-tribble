import pytest
from httpx import AsyncClient

from app.models import Document


class TestDocumentsComprehensive:
    """Comprehensive document tests for full coverage."""

    @pytest.mark.asyncio
    async def test_create_document_full(self, client: AsyncClient, auth_headers):
        """Test creating document with all fields."""
        response = await client.post(
            "/api/documents",
            headers=auth_headers,
            json={
                "title": "Complete Document",
                "description": "Full description",
                # "content": "Full content here",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Complete Document"
        assert data["description"] == "Full description"
        # assert data["content"] == "Full content here"

    @pytest.mark.asyncio
    async def test_create_document_minimal(self, client: AsyncClient, auth_headers):
        """Test creating document with minimal fields."""
        response = await client.post(
            "/api/documents",
            headers=auth_headers,
            json={
                "title": "Minimal Doc",
                # "content": "Content",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get_document_success(self, client: AsyncClient, auth_headers, test_document):
        """Test getting existing document."""
        response = await client.get(f"/api/documents/{test_document.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent document."""
        response = await client.get("/api/documents/999999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_document_title_only(
        self, client: AsyncClient, auth_headers, test_document
    ):
        """Test updating only title."""
        response = await client.put(
            f"/api/documents/{test_document.id}",
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
            f"/api/documents/{test_document.id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "description": "Updated Description",
                # "content": "Updated Content"
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated Description"
        # assert data["content"] == "Updated Content"

    @pytest.mark.asyncio
    async def test_delete_document_success(self, client: AsyncClient, auth_headers, test_document):
        """Test deleting document."""
        response = await client.delete(f"/api/documents/{test_document.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(f"/api/documents/{test_document.id}", headers=auth_headers)
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

        response = await client.get("/api/documents", headers=headers)
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
                # description=f"Description {i}",
                owner_id=test_user.id,
            )
            session.add(doc)
        await session.commit()

        # Get first page
        response = await client.get("/api/documents?page=1&page_size=10", headers=auth_headers)
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
            title="Python Tutorial", description="Learn Python programming", owner_id=test_user.id
        )
        doc2 = Document(
            title="JavaScript Guide", description="Learn JavaScript", owner_id=test_user.id
        )
        session.add_all([doc1, doc2])
        await session.commit()

        # Search for Python
        response = await client.get("/api/documents?search=Python", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert any("Python" in item["title"] for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_documents_sort_asc(self, client: AsyncClient, auth_headers):
        """Test sorting documents ascending."""
        response = await client.get(
            "/api/documents?sort_by=title&sort_order=asc", headers=auth_headers
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
            "/api/documents?sort_by=created_at&sort_order=desc", headers=auth_headers
        )
        assert response.status_code == 200
