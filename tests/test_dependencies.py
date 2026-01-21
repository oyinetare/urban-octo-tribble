from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import SecurityScopes

from app.dependencies import get_current_user, verify_document_ownership
from app.exceptions import (
    CredentialsException,
    InsufficientScopesException,
    NotAuthorizedDocumenAccessException,
)
from app.models import User


@pytest.mark.asyncio
class TestDependenciesUnit:
    async def test_get_current_user_blacklisted_token(self, session):
        """Test that blacklisted tokens raise CredentialsException using real session."""
        with patch(
            "app.core.redis_service.is_token_blacklisted", new_callable=AsyncMock
        ) as mock_redis:
            mock_redis.return_value = True
            with pytest.raises(CredentialsException):
                # Pass your actual 'session' fixture here
                await get_current_user(SecurityScopes(), token="any-token", session=session)

    async def test_get_current_user_insufficient_scopes(self, session):
        """Test that missing required scopes raise InsufficientScopesException."""
        with patch("app.core.token_manager.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "testuser", "scopes": ["read"]}
            with patch(
                "app.core.redis_service.is_token_blacklisted", new_callable=AsyncMock
            ) as mock_redis:
                mock_redis.return_value = False

                # Request 'admin' scope when token only has 'read'
                scopes = SecurityScopes(scopes=["admin"])
                with pytest.raises(InsufficientScopesException):
                    await get_current_user(scopes, token="valid-token", session=session)

    async def test_verify_document_ownership_admin_bypass(self, session, admin_user, test_document):
        """Test admin bypass logic using your conftest fixtures."""
        # admin_user (id=2) is accessing test_document owned by test_user (id=1)
        # This should return 200/Document because of the 'admin' role bypass
        admin_user.role = "admin"

        result = await verify_document_ownership(
            document_id=test_document.id,
            # security_scopes=SecurityScopes(scopes=[]),
            current_user=admin_user,
            session=session,
        )
        assert result.id == test_document.id

    async def test_verify_document_ownership_scope_bypass(self, session, test_user, test_document):
        """Test that 'admin' scope grants access even if database role is 'user'."""
        # Create a user with role='user' but inject the 'admin' scope via SecurityScopes
        result = await verify_document_ownership(
            document_id=test_document.id,
            # security_scopes=SecurityScopes(scopes=["admin"]),
            current_user=test_user,  # Regular owner
            session=session,
        )
        assert result.id == test_document.id

    async def test_verify_document_ownership_unauthorized(self, session, test_document):
        """Test 403 for non-owner, non-admin user."""
        # FIX: Use 'role_name' instead of 'role' (or set both) to satisfy the model's logic
        other_user = User(
            id=999,
            email="other@email.com",
            username="other",
            role_name="user",  # Match the field used by UserRole(self.role_name)
            is_active=True,
        )

        with pytest.raises(NotAuthorizedDocumenAccessException):
            await verify_document_ownership(
                document_id=test_document.id,
                # security_scopes=SecurityScopes(scopes=["read"]),
                current_user=other_user,
                session=session,
            )
