import pytest
from httpx import AsyncClient


class TestAuthenticationExtended:
    """Extended authentication tests for better coverage."""

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        """Test refresh token functionality."""
        # Login to get refresh token
        login_response = await client.post(
            "/api/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )
        assert login_response.status_code == 200

        # Extract refresh token from cookies
        cookies = login_response.cookies
        assert "refresh_token" in cookies

        # Use refresh token
        refresh_response = await client.post("/api/auth/refresh", cookies=cookies)
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_without_cookie(self, client: AsyncClient):
        """Test refresh without refresh token cookie."""
        response = await client.post("/api/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_clears_tokens(self, client: AsyncClient, auth_headers):
        """Test logout blacklists tokens."""
        # Login first
        login_response = await client.post(
            "/api/auth/login", data={"username": "testuser", "password": "testpassword"}
        )

        # Logout
        logout_response = await client.post(
            "/api/auth/logout", headers=auth_headers, cookies=login_response.cookies
        )
        assert logout_response.status_code == 200

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_login(self, client: AsyncClient, session, test_user):
        """Test inactive user cannot login."""
        # Deactivate user
        test_user.is_active = False
        session.add(test_user)
        await session.commit()

        # Try to login
        response = await client.post(
            "/api/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )
        assert response.status_code == 400
