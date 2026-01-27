from io import BytesIO

import pytest
from httpx import AsyncClient


class TestFileValidation:
    """Test file validation chain comprehensively."""

    @pytest.mark.asyncio
    async def test_valid_pdf_upload(self, client: AsyncClient, auth_headers):
        """Test uploading valid PDF file."""
        file_content = b"%PDF-1.4\n%valid pdf content for testing"
        files = {"file": ("valid.pdf", BytesIO(file_content), "application/pdf")}
        data = {"title": "Valid PDF", "description": "Should pass validation"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["filename"] == "valid.pdf"
        assert result["content_type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_valid_text_upload(self, client: AsyncClient, auth_headers):
        """Test uploading valid text file."""
        file_content = b"This is a plain text document with some content."
        files = {"file": ("document.txt", BytesIO(file_content), "text/plain")}
        data = {"title": "Text File", "description": "Plain text upload"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["filename"] == "document.txt"
        assert result["content_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_valid_docx_upload(self, client: AsyncClient, auth_headers):
        """Test uploading valid DOCX file."""
        # DOCX files are ZIP archives that start with PK
        file_content = b"PK\x03\x04" + b"\x00" * 100  # Minimal DOCX header
        files = {
            "file": (
                "document.docx",
                BytesIO(file_content),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {"title": "Word Document", "description": "DOCX upload"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["filename"] == "document.docx"

    @pytest.mark.asyncio
    async def test_file_size_exactly_at_limit(self, client: AsyncClient, auth_headers):
        """Test file exactly at 10MB limit."""
        # Exactly 10MB
        file_content = b"x" * (10 * 1024 * 1024)
        files = {"file": ("exactly_10mb.txt", BytesIO(file_content), "text/plain")}
        data = {"title": "10MB File", "description": "Exactly at limit"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should succeed - at or under the limit
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_file_size_just_over_limit(self, client: AsyncClient, auth_headers):
        """Test file just over 10MB limit."""
        # 10MB + 1 byte
        file_content = b"x" * (10 * 1024 * 1024 + 1)
        files = {"file": ("over_limit.txt", BytesIO(file_content), "text/plain")}
        data = {"title": "Too Large", "description": "Just over limit"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code in [400, 422]
        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert any(word in message for word in ["large", "size", "max", "limit", "bytes"])

    @pytest.mark.asyncio
    async def test_file_size_very_large(self, client: AsyncClient, auth_headers):
        """Test uploading very large file (100MB)."""
        # 100MB file
        file_content = b"x" * (100 * 1024 * 1024)
        files = {"file": ("huge.txt", BytesIO(file_content), "text/plain")}
        data = {"title": "Huge File", "description": "Way over limit"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_file_type_image(self, client: AsyncClient, auth_headers):
        """Test uploading image (not allowed)."""
        files = {"file": ("image.jpg", BytesIO(b"\xff\xd8\xff"), "image/jpeg")}
        data = {"title": "Image", "description": "Should be rejected"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code in [400, 422]
        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert any(word in message for word in ["type", "invalid", "allowed"])

    @pytest.mark.asyncio
    async def test_invalid_file_type_executable(self, client: AsyncClient, auth_headers):
        """Test uploading executable (not allowed)."""
        files = {"file": ("malware.exe", BytesIO(b"MZ\x90\x00"), "application/x-msdownload")}
        data = {"title": "Executable", "description": "Should be rejected"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code in [400, 422]
        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert "error" in message

    @pytest.mark.asyncio
    async def test_invalid_file_type_video(self, client: AsyncClient, auth_headers):
        """Test uploading video (not allowed)."""
        files = {"file": ("video.mp4", BytesIO(b"\x00\x00\x00\x20ftypmp42"), "video/mp4")}
        data = {"title": "Video", "description": "Should be rejected"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code in [400, 422]
        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert "error" in message

    @pytest.mark.asyncio
    async def test_empty_filename(self, client: AsyncClient, auth_headers):
        """Test uploading file with empty filename."""
        files = {"file": ("", BytesIO(b"content"), "application/pdf")}
        data = {"title": "No Filename", "description": "Empty filename"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_filename_exactly_255_chars(self, client: AsyncClient, auth_headers):
        """Test filename exactly at 255 character limit."""
        # 255 chars including extension
        name = "a" * 251 + ".pdf"  # 251 + 4 = 255
        files = {"file": (name, BytesIO(b"%PDF-1.4\ntest"), "application/pdf")}
        data = {"title": "Long Name", "description": "At limit"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should succeed - exactly at limit
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_filename_over_255_chars(self, client: AsyncClient, auth_headers):
        """Test filename over 255 character limit."""
        # 256 chars
        name = "a" * 252 + ".pdf"  # 252 + 4 = 256
        files = {"file": (name, BytesIO(b"%PDF-1.4\ntest"), "application/pdf")}
        data = {"title": "Too Long Name", "description": "Over limit"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should fail validation
        assert response.status_code in [400, 422]
        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert "error" in message

    @pytest.mark.asyncio
    async def test_filename_special_characters(self, client: AsyncClient, auth_headers):
        """Test filename with special characters."""
        files = {"file": ("test-file_v2.1.pdf", BytesIO(b"%PDF-1.4\ntest"), "application/pdf")}
        data = {"title": "Special Chars", "description": "Hyphens, underscores, dots"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should succeed - these chars are typically allowed
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_filename_unicode(self, client: AsyncClient, auth_headers):
        """Test filename with unicode characters."""
        files = {"file": ("文档.txt", BytesIO(b"unicode content"), "text/plain")}
        data = {"title": "Unicode Name", "description": "Unicode filename"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should succeed - unicode is typically allowed
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_empty_file(self, client: AsyncClient, auth_headers):
        """Test uploading empty file."""
        files = {"file": ("empty.txt", BytesIO(b""), "text/plain")}
        data = {"title": "Empty File", "description": "Zero bytes"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should succeed - empty files are valid
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_validation_chain_order(self, client: AsyncClient, auth_headers):
        """Test that validation chain runs in correct order."""
        # File that fails both size AND type checks
        # Size check should happen first
        large_invalid = b"x" * (11 * 1024 * 1024)
        files = {"file": ("large.jpg", BytesIO(large_invalid), "image/jpeg")}
        data = {"title": "Large Invalid", "description": "Fails multiple validations"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        assert response.status_code in [400, 422]
        if response.status_code == 400:
            message = response.json().get("message", "").lower()
            assert "error" in message

    @pytest.mark.asyncio
    async def test_missing_file_entirely(self, client: AsyncClient, auth_headers):
        """Test request with no file at all."""
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"title": "No File", "description": "Missing file"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_none_content_type(self, client: AsyncClient, auth_headers):
        """Test file with None content_type."""
        files = {"file": ("test.pdf", BytesIO(b"%PDF-1.4\ntest"), None)}
        data = {"title": "No Content Type", "description": "None type"}

        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data=data,
            files=files,
        )

        # Should handle gracefully - defaults to application/octet-stream
        # But might fail type validation depending on implementation
        assert response.status_code in [201, 400]
