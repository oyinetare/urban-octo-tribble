"""
Diagnostic test to understand what's happening with the endpoints.
Run this first to see actual responses.
"""

from io import BytesIO

import pytest
from httpx import AsyncClient


class TestDiagnostic:
    """Diagnostic tests to see actual responses."""

    @pytest.mark.asyncio
    async def test_deprecated_endpoint_behavior(self, client: AsyncClient, auth_headers):
        """See what the deprecated endpoint actually returns."""
        response = await client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={"title": "Test", "description": "Test"},
        )

        print("\n=== DEPRECATED ENDPOINT ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"JSON: {response.json() if response.status_code != 500 else 'ERROR'}")

    @pytest.mark.asyncio
    async def test_upload_too_large_actual(self, client: AsyncClient, auth_headers):
        """See what large file actually returns."""
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        data = {"title": "Large", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        print("\n=== LARGE FILE UPLOAD ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

    @pytest.mark.asyncio
    async def test_invalid_type_actual(self, client: AsyncClient, auth_headers):
        """See what invalid type actually returns."""
        files = {"file": ("test.jpg", BytesIO(b"fake"), "image/jpeg")}
        data = {"title": "Image", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        print("\n=== INVALID FILE TYPE ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

    @pytest.mark.asyncio
    async def test_long_filename_actual(self, client: AsyncClient, auth_headers):
        """See what long filename actually returns."""
        name = "a" * 300 + ".pdf"
        files = {"file": (name, BytesIO(b"%PDF-1.4\ntest"), "application/pdf")}
        data = {"title": "Long", "description": "Test"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        print("\n=== LONG FILENAME ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
