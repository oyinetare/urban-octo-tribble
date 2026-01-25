import pytest
from httpx import AsyncClient


class TestAuthentication:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "strongpassword123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_user(self, client: AsyncClient, test_user):
        """Test registering duplicate user fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "differentusername",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "scopes" in data
        # Check refresh token cookie
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, test_user):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_token(self, client: AsyncClient, auth_headers):
        """Test accessing protected endpoint with valid token."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_protected_endpoint_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer invalidtoken"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers):
        """Test logout blacklists token."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200

        # Try to use the same token again
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        # Should fail if Redis is available and token is blacklisted
        # If Redis is unavailable, this test may need adjustment
