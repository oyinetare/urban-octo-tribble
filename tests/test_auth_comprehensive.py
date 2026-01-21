import pytest
from httpx import AsyncClient


class TestAuthComprehensive:
    """Comprehensive auth tests to reach 85% coverage."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "username": "different",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        """Test registration with duplicate username."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@test.com",
                "username": test_user.username,
                "password": "password123",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success_with_cookie(self, client: AsyncClient, test_user):
        """Test login sets refresh token cookie."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )
        assert response.status_code == 200

        # Check access token in response
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "scopes" in data

        # Check refresh token in cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_updates_last_login(self, client: AsyncClient, test_user, session):
        """Test that login updates last_login timestamp."""
        old_last_login = test_user.last_login

        await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )

        # Refresh user from DB
        await session.refresh(test_user)
        assert test_user.last_login > old_last_login

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login with wrong password."""
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
    async def test_login_inactive_user(self, client: AsyncClient, session):
        """Test login with inactive user."""
        from app.core import token_manager
        from app.models import User

        inactive_user = User(
            email="inactive@test.com",
            username="inactive",
            hashed_password=token_manager.get_password_hash("password"),
            role="user",
            is_active=False,
        )
        session.add(inactive_user)
        await session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "inactive",
                "password": "password",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user):
        """Test refreshing access token."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )

        # Get cookies
        cookies = login_response.cookies

        # Refresh token
        response = await client.post("/api/v1/auth/refresh", cookies=cookies)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "scopes" in data

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, client: AsyncClient):
        """Test refresh without token."""
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_type(self, client: AsyncClient):
        """Test refresh with access token instead of refresh token."""
        from app.core import token_manager

        # Create access token (wrong type)
        access_token = token_manager.create_access_token(data={"sub": "test", "scopes": ["read"]})

        response = await client.post(
            "/api/v1/auth/refresh", cookies={"refresh_token": access_token}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers):
        """Test logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()
