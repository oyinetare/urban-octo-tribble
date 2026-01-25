import pytest
from httpx import AsyncClient
from sqlmodel import func, select

from app.core import token_manager
from app.models import Document, User


class TestDocuments:
    """Test document CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document(self, client: AsyncClient, auth_headers):
        """Test creating a document."""
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={
                "title": "New Document",
                "description": "Test Description",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Document"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_document_without_auth(self, client: AsyncClient):
        """Test creating document without authentication fails."""
        response = await client.post(
            "/api/v1/documents", json={"title": "Test", "description": "Test"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_document(self, client: AsyncClient, auth_headers, test_document):
        """Test getting a document."""
        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id
        assert data["title"] == test_document.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, client: AsyncClient, auth_headers):
        """Test getting non-existent document returns 404."""
        response = await client.get("/api/v1/documents/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_user_document(self, client: AsyncClient, session, test_document):
        """Test getting another user's document returns 403."""
        # Create another user
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=token_manager.get_password_hash("password"),
            role="user",
        )
        session.add(other_user)
        await session.commit()

        # Get token for other user
        token = token_manager.create_access_token(
            data={"sub": other_user.username, "scopes": ["read", "write"]}
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_document(self, client: AsyncClient, auth_headers, test_document):
        """Test updating a document."""
        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_document(self, client: AsyncClient, auth_headers, test_document):
        """Test deleting a document."""
        response = await client.delete(
            f"/api/v1/documents/{test_document.id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify document is deleted
        response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test listing documents with pagination."""
        # Create 25 documents
        for i in range(25):
            doc = Document(
                title=f"Document {i:02d}",  # Using padding for consistent sorting
                description=f"Description {i}",
                owner_id=test_user.id,
            )
            session.add(doc)

        await session.commit()
        # No need to refresh 25 docs, but ensures the session is clean
        await session.execute(select(func.count(Document.id)))

        # Test first page
        response = await client.get("/api/v1/documents?page=1&page_size=10", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_list_documents_filtering(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test filtering documents by search term."""
        doc1 = Document(title="Python Tutorial", description="Learn Python", owner_id=test_user.id)
        doc2 = Document(title="JavaScript Guide", description="Learn JS", owner_id=test_user.id)
        session.add_all([doc1, doc2])
        await session.commit()

        response = await client.get("/api/v1/documents?search=Python", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Python Tutorial"

    @pytest.mark.asyncio
    async def test_list_documents_sorting(self, client: AsyncClient, auth_headers):
        """Test sorting documents."""
        response = await client.get(
            "/api/v1/documents?sort_by=title&sort_order=asc", headers=auth_headers
        )
        assert response.status_code == 200
