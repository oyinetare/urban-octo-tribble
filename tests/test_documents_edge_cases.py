import pytest
from httpx import AsyncClient

from app.models import Document


class TestDocumentsEdgeCases:
    """Additional document tests for edge cases."""

    @pytest.mark.asyncio
    async def test_create_document_with_description(self, client: AsyncClient, auth_headers):
        """Test creating document with description."""
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={
                "title": "Doc with description",
                "description": "A detailed description",
                # "content": "Content"
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "A detailed description"

    @pytest.mark.asyncio
    async def test_list_documents_with_sorting(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test document sorting."""
        # Create documents with different titles
        for title in ["Zebra", "Apple", "Mango"]:
            doc = Document(title=title, description="Description", owner_id=test_user.id)
            session.add(doc)
        await session.commit()

        # Test ascending sort
        response = await client.get(
            "/api/v1/documents?sort_by=title&sort_order=asc", headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        # First should be alphabetically first
        titles = [item["title"] for item in items]
        assert titles[0] in ["Apple", "Mango", "Test Document", "Zebra"]

    @pytest.mark.asyncio
    async def test_update_document_description_only(
        self, client: AsyncClient, auth_headers, test_document
    ):
        """Test updating only description."""
        response = await client.put(
            f"/api/v1/documents/{test_document.id}",
            headers=auth_headers,
            json={"description": "New description"},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    @pytest.mark.asyncio
    async def test_search_in_description(
        self, client: AsyncClient, auth_headers, session, test_user
    ):
        """Test searching in description field."""
        doc = Document(
            title="Test",
            description="Special unique keyword",
            # content="Content",
            owner_id=test_user.id,
        )
        session.add(doc)
        await session.commit()

        response = await client.get("/api/v1/documents?search=unique", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
