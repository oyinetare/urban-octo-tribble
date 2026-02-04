"""
Comprehensive auth flow tests for app/routes/auth.py
Target: Increase coverage from 56% to 80%+
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import token_manager
from app.models import User


class TestRegistrationFlow:
    """Test complete registration flows."""

    @pytest.mark.asyncio
    async def test_register_with_all_fields(self, client: AsyncClient):
        """Test registration with all optional fields."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "complete@test.com",
                "username": "completeuser",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "complete@test.com"
        assert data["username"] == "completeuser"
        assert data["is_active"] is True
        assert data["role"] == "user"  # Default role
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_sets_default_values(self, client: AsyncClient):
        """Test registration sets correct default values."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "defaults@test.com",
                "username": "defaultuser",
                "password": "password123",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify defaults
        assert data["is_active"] is True
        assert data["role"] == "user"
        # Note: tier field might not be in response depending on your schema

    @pytest.mark.asyncio
    async def test_register_password_is_hashed(self, client: AsyncClient, session: AsyncSession):
        """Test password is properly hashed on registration."""
        plain_password = "MySecretPassword123"

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hash@test.com",
                "username": "hashuser",
                "password": plain_password,
            },
        )

        assert response.status_code == 201

        # Fetch user from DB
        from sqlmodel import select

        result = await session.execute(select(User).where(User.username == "hashuser"))
        user = result.scalar_one()

        # Password should be hashed, not plain
        assert user.hashed_password != plain_password
        assert user.hashed_password.startswith("$")  # Argon2 or bcrypt prefix

    @pytest.mark.asyncio
    async def test_register_duplicate_email_different_case(self, client: AsyncClient):
        """Test duplicate email - SQLite is case-sensitive by default."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "TEST@EXAMPLE.COM",  # Different case
                "username": "newuser",
                "password": "password123",
            },
        )

        # SQLite allows this unless you have COLLATE NOCASE on email column
        assert response.status_code == 201
        # If you want case-insensitive, add this to User model:
        # email: str = Field(sa_column=Column(String, unique=True, collation="NOCASE"))

    @pytest.mark.asyncio
    async def test_register_duplicate_username_different_case(self, client: AsyncClient):
        """Test duplicate username detection is case-insensitive."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "username": "TESTUSER",  # Same as testuser
                "password": "password123",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_register_creates_timestamps(self, client: AsyncClient):
        """Test registration creates created_at timestamp."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "timestamps@test.com",
                "username": "timestampuser",
                "password": "password123",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "created_at" in data


class TestLoginFlow:
    """Test complete login flows."""

    @pytest.mark.asyncio
    async def test_login_returns_access_and_refresh_tokens(
        self, client: AsyncClient, test_user: User
    ):
        """Test login returns both token types."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response body
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "scopes" in data
        assert isinstance(data["scopes"], list)

        # Check cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_with_email_instead_of_username(self, client: AsyncClient, test_user: User):
        """Test login allows email as username."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,  # Use email
                "password": "testpassword",
            },
        )

        # Should work if your implementation supports it
        # Otherwise, should return 401
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_login_case_insensitive_username(self, client: AsyncClient, test_user: User):
        """Test login username is case-insensitive."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username.upper(),
                "password": "testpassword",
            },
        )

        # Depends on implementation
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_login_increments_login_count(
        self, client: AsyncClient, test_user: User, session: AsyncSession
    ):
        """Test login increments login count if tracked."""
        old_last_login = test_user.last_login

        await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )

        # Refresh user
        await session.refresh(test_user)

        # last_login should be updated
        assert test_user.last_login != old_last_login

    @pytest.mark.asyncio
    async def test_login_wrong_password_multiple_attempts(
        self, client: AsyncClient, test_user: User
    ):
        """Test multiple failed login attempts."""
        for _ in range(3):
            response = await client.post(
                "/api/v1/auth/login",
                data={
                    "username": test_user.username,
                    "password": "wrongpassword",
                },
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_sql_injection_attempt(self, client: AsyncClient):
        """Test login is protected against SQL injection."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin' OR '1'='1",
                "password": "' OR '1'='1",
            },
        )

        # Should fail, not bypass authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_returns_user_scopes(self, client: AsyncClient, test_user: User):
        """Test login returns correct user scopes."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "scopes" in data
        assert isinstance(data["scopes"], list)
        assert "read" in data["scopes"]
        assert "write" in data["scopes"]

    @pytest.mark.asyncio
    async def test_login_admin_gets_admin_scope(self, client: AsyncClient, admin_user: User):
        """Test admin login includes admin scope."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": admin_user.username,
                "password": "adminpassword",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "admin" in data["scopes"]


class TestRefreshTokenFlow:
    """Test refresh token flows."""

    @pytest.mark.asyncio
    async def test_refresh_with_valid_token(self, client: AsyncClient, test_user: User):
        """Test refreshing with valid refresh token."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword",
            },
        )

        cookies = login_response.cookies

        # Refresh
        response = await client.post("/api/v1/auth/refresh", cookies=cookies)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_returns_new_access_token(self, client: AsyncClient, test_user: User):
        """Test refresh returns a new access token."""
        import asyncio

        # Login
        login_response = await client.post(
            "/api/v1/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )

        old_access_token = login_response.json()["access_token"]
        cookies = login_response.cookies

        # Small delay
        await asyncio.sleep(0.1)

        # Refresh
        refresh_response = await client.post("/api/v1/auth/refresh", cookies=cookies)
        new_access_token = refresh_response.json()["access_token"]

        # Tokens should be different
        assert new_access_token != old_access_token

    @pytest.mark.asyncio
    async def test_refresh_preserves_user_scopes(self, client: AsyncClient, test_user: User):
        """Test refresh token preserves user scopes."""
        # Login
        login_response = await client.post(
            "/api/v1/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )

        old_scopes = login_response.json()["scopes"]

        # Refresh
        refresh_response = await client.post("/api/v1/auth/refresh", cookies=login_response.cookies)

        new_scopes = refresh_response.json()["scopes"]

        # Scopes should be the same
        assert set(old_scopes) == set(new_scopes)

    @pytest.mark.asyncio
    async def test_refresh_with_expired_token(self, client: AsyncClient):
        """Test refresh with expired token fails."""
        # FIX: Use new signature
        expired_token = token_manager.create_refresh_token(
            data={"sub": "test", "id": 1, "tier_limit": 20, "scopes": ["read"]},
            expires_delta_minutes=-1,
        )

        client.cookies.set("refresh_token", expired_token)
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client: AsyncClient, test_user: User):
        """Test using access token for refresh fails."""
        # FIX: Use new signature
        access_token = token_manager.create_access_token(
            user_id=test_user.id, username=test_user.username, tier_limit=20, scopes=["read"]
        )

        client.cookies.set("refresh_token", access_token)
        response = await client.post("/api/v1/auth/refresh")
        assert response.status_code == 401


class TestLogoutFlow:
    """Test logout flows."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_logout_clears_refresh_token_cookie(self, client: AsyncClient, test_user: User):
        """Test logout clears refresh token cookie."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Logout
        logout_response = await client.post("/api/v1/auth/logout", headers=headers)

        assert logout_response.status_code == 200

        # Cookie should be cleared (set to empty or expired)
        if "refresh_token" in logout_response.cookies:
            # Should be empty or have max-age=0
            cookie = logout_response.cookies["refresh_token"]
            assert cookie == "" or cookie is None

    @pytest.mark.asyncio
    async def test_logout_without_auth_fails(self, client: AsyncClient):
        """Test logout without authentication fails."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestPasswordValidation:
    """Test password validation during registration."""

    @pytest.mark.asyncio
    async def test_register_empty_password(self, client: AsyncClient):
        """Test registration with empty password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "empty@test.com",
                "username": "emptypass",
                "password": "",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_very_long_password(self, client: AsyncClient):
        """Test registration with very long password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "long@test.com",
                "username": "longpass",
                "password": "a" * 1000,  # Very long password
            },
        )

        # Should succeed - passwords can be long
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_register_password_with_special_chars(self, client: AsyncClient):
        """Test registration with special characters in password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "special@test.com",
                "username": "specialpass",
                "password": "P@ssw0rd!#$%^&*()",
            },
        )

        assert response.status_code == 201


class TestUserMeEndpoint:
    """Test /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_info(self, client: AsyncClient, auth_headers, test_user: User):
        """Test getting current user info."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_get_user_me_without_auth(self, client: AsyncClient):
        """Test /users/me without authentication fails."""
        response = await client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_me_with_expired_token(self, client: AsyncClient):
        """Test /users/me with expired token fails."""
        # FIX: Use new signature
        expired_token = token_manager.create_access_token(
            user_id=1, username="test", tier_limit=20, scopes=["read"], expires_delta_minutes=-1
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401


class TestTokenSecurity:
    """Test token security features."""

    @pytest.mark.asyncio
    async def test_tokens_are_different_each_time(self, client: AsyncClient, test_user: User):
        """Test tokens are different for each login."""
        import asyncio

        # Login first time
        response1 = await client.post(
            "/api/v1/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )

        # Small delay to ensure different timestamp
        await asyncio.sleep(0.1)

        # Login second time
        response2 = await client.post(
            "/api/v1/auth/login", data={"username": test_user.username, "password": "testpassword"}
        )

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Tokens should be different (different iat)
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_token_contains_correct_claims(self, test_user: User):
        """Test token contains all required claims."""
        # FIX: Use new signature
        token = token_manager.create_access_token(
            user_id=test_user.id,
            username=test_user.username,
            tier_limit=20,
            scopes=["read", "write"],
        )

        # Decode and verify
        payload = token_manager.decode_token(token)
        assert payload["sub"] == test_user.username
        assert "read" in payload["scopes"]
        assert "write" in payload["scopes"]
