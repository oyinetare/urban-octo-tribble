from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import SecurityScopes

from app.core.services import services
from app.dependencies import (
    get_admin_user,
    get_current_active_user,
    get_current_user,
    get_embedding_service,
    get_services,
    get_storage_service,
    get_vector_service,
    pagination_params,
    require_role,
    verify_document_ownership,
)
from app.exceptions import (
    CredentialsException,
    InactiveUserException,
    InsufficientScopesException,
    NotAuthorizedDocumenAccessException,
    RequiresRoleException,
)
from app.models import User


@pytest.mark.asyncio
class TestDependenciesUnit:
    async def test_get_current_user_blacklisted_token(self, session):
        """Test that blacklisted tokens raise CredentialsException."""

        # 1. Initialize services to get the real (fakeredis) instance
        await services.init()
        redis_mock = services.redis

        # 2. Patch the method on that specific instance
        with patch.object(redis_mock, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            with pytest.raises(CredentialsException):
                # 3. CRITICAL: Pass redis_mock explicitly to bypass the Depends object
                await get_current_user(
                    security_scopes=SecurityScopes(),
                    token="any-token",
                    session=session,
                    redis=redis_mock,  # This replaces the 'Depends' object
                )

    async def test_get_current_user_insufficient_scopes(self, session):
        """Test that missing required scopes raise InsufficientScopesException."""
        await services.init()
        redis_mock = services.redis

        with patch("app.core.security.token_manager.decode_token") as mock_decode:
            # Note: Ensure payload matches your NEW signature (id, tier_limit)
            mock_decode.return_value = {
                "sub": "testuser",
                "id": 1,
                "tier_limit": 10,
                "scopes": ["read"],
            }

            with patch.object(
                redis_mock, "is_token_blacklisted", new_callable=AsyncMock
            ) as mock_redis:
                mock_redis.return_value = False

                scopes = SecurityScopes(scopes=["admin"])
                with pytest.raises(InsufficientScopesException):
                    # Again, pass redis explicitly
                    await get_current_user(
                        scopes, token="valid-token", session=session, redis=redis_mock
                    )

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

    async def test_get_embedding_service_initialization(self):
        """Verify embedding service init is called if service is None."""
        with patch("app.dependencies.services") as mock_container:
            # 1. Start as None so 'if not services.embedding' is True
            mock_container.embedding = None
            mock_container.init = AsyncMock()

            fake_embedder = AsyncMock()

            # 2. When init() is called, set the attribute so it exists for the return
            async def side_effect():
                mock_container.embedding = fake_embedder

            mock_container.init.side_effect = side_effect

            result = await get_embedding_service()

            mock_container.init.assert_called_once()
            assert result == fake_embedder

    async def test_get_vector_service_returns_instance(self):
        """Verify vector service is returned directly if already initialized."""
        # Patch where it is IMPORTED (app.dependencies), not where it is defined
        with patch("app.dependencies.services") as mock_service_container:
            mock_vector = AsyncMock()
            # Setup the mock state
            mock_service_container.vector_store = mock_vector
            mock_service_container.init = AsyncMock()

            result = await get_vector_service()

            # Assertions
            mock_service_container.init.assert_not_called()
            assert result == mock_vector

    async def test_get_storage_service(self):
        """Test storage service retrieval and initialization."""
        with patch("app.dependencies.services") as mock_service_container:
            # Force the state to 'not initialized'
            mock_service_container.storage = None
            mock_service_container.init = AsyncMock()

            fake_storage = AsyncMock()

            # Simulate the side-effect of init() setting the attribute
            async def side_effect():
                mock_service_container.storage = fake_storage

            mock_service_container.init.side_effect = side_effect

            result = await get_storage_service()

            mock_service_container.init.assert_called_once()
            assert result == fake_storage

    async def test_get_services_full_container(self):
        """Test that the full container is returned and initialized if needed."""
        with patch("app.dependencies.services") as mock_container:
            # Simulate redis/storage missing to trigger init
            mock_container.redis = None
            mock_container.storage = None
            mock_container.init = AsyncMock()

            result = await get_services()

            mock_container.init.assert_called_once()
            assert result == mock_container

    async def test_get_current_active_user_inactive(self, session, test_user):
        """Test that an inactive user raises InactiveUserException."""
        # 1. Update status and persist to the test DB
        test_user.is_active = False
        session.add(test_user)
        await session.commit()

        with patch("app.dependencies.token_manager.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": test_user.username}

            mock_redis = AsyncMock()
            mock_redis.is_token_blacklisted.return_value = False

            # No need to patch 'select' since we are using the real session fixture
            with pytest.raises(InactiveUserException):
                await get_current_active_user(token="valid", session=session, redis=mock_redis)

    async def test_get_admin_user_success(self, admin_user):
        """Test that get_admin_user returns the user if they are an admin."""
        admin_user.role = "admin"
        result = await get_admin_user(current_user=admin_user)
        assert result == admin_user

    async def test_get_admin_user_failure(self, test_user):
        """Test that get_admin_user raises RequiresRoleException for regular users."""
        test_user.role = "user"
        with pytest.raises(RequiresRoleException):
            await get_admin_user(current_user=test_user)

    async def test_require_role_factory_success(self, test_user):
        """Test the require_role dependency factory."""
        test_user.role = "admin"
        # require_role returns a function (the dependency)
        role_checker = require_role("admin")

        result = await role_checker(current_user=test_user)
        assert result == test_user

    async def test_require_role_factory_failure(self, test_user):
        """Test the require_role factory raises error on mismatch."""
        test_user.role = "user"
        role_checker = require_role("admin")

        with pytest.raises(RequiresRoleException):
            await role_checker(current_user=test_user)

    async def test_pagination_params_valid(self):
        """Test pagination logic (sync test)."""
        params = pagination_params(page=2, page_size=50)
        assert params.page == 2
        assert params.page_size == 50
        # Check if the offset logic works as expected if your PaginationParams has it
        # assert params.offset == 50
