import pytest

from app.models import Document


class TestModels:
    """Test model functionality."""

    @pytest.mark.asyncio
    async def test_user_model_creation(self, session):
        """Test creating user model."""
        from app.core import token_manager
        from app.models import User

        user = User(
            email="model@test.com",
            username="modeluser",
            hashed_password=token_manager.get_password_hash("password"),
            role="user",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.email == "model@test.com"
        assert user.is_active is True
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_user_roles(self):
        """Test user role scopes."""
        from app.core.constants import UserRole

        assert "read" in UserRole.USER.scopes
        assert "write" in UserRole.USER.scopes
        assert "admin" in UserRole.ADMIN.scopes
        assert "moderate" in UserRole.MODERATOR.scopes

    @pytest.mark.asyncio
    async def test_user_tiers(self):
        """Test user tier limits."""
        from app.core.constants import UserTier

        assert UserTier.FREE.limit == 10
        assert UserTier.PAID.limit == 100
        assert UserTier.ENTERPRISE.limit == 1000

    @pytest.mark.asyncio
    async def test_document_model_creation(self, session, test_user):
        """Test creating document model."""
        doc = Document(
            title="Model Test",
            description="Description",
            owner_id=test_user.id,
            storage_key="temporary_key",
            filename="Test.pdf",
            file_size=1024,
            content_type="application/octet-stream",
            status="pending",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.id is not None
        assert doc.title == "Model Test"
        assert doc.owner_id == test_user.id
        assert doc.created_at is not None

    @pytest.mark.asyncio
    async def test_short_url_model(self, session, test_document):
        """Test short URL model."""
        from app.models import ShortURL

        short = ShortURL(short_code="test123", document_id=test_document.id, clicks=0)
        session.add(short)
        await session.commit()
        await session.refresh(short)

        assert short.short_code == "test123"
        assert short.clicks == 0
        assert short.created_at is not None

    @pytest.mark.asyncio
    async def test_user_role_scopes(self):
        """Test user role scope mapping."""
        from app.core.constants import UserRole

        assert "read" in UserRole.USER.scopes
        assert "write" in UserRole.USER.scopes
        assert "admin" in UserRole.ADMIN.scopes
        assert "moderate" in UserRole.MODERATOR.scopes

    @pytest.mark.asyncio
    async def test_user_tier_limits(self):
        """Test user tier rate limits."""
        from app.core.constants import UserTier

        assert UserTier.FREE.limit == 10
        assert UserTier.PAID.limit == 100
        assert UserTier.ENTERPRISE.limit == 1000

    @pytest.mark.asyncio
    async def test_sort_order_enum(self):
        """Test sort order enum."""
        from app.core.constants import SortOrder

        assert SortOrder.ASC == "asc"
        assert SortOrder.DESC == "desc"
