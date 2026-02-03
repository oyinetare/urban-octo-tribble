from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.core import UserRole, UserTier
from app.models.base import BaseModel
from app.utility import utc_now

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models import Document, Query


class User(BaseModel, table=True):
    """User database model."""

    __tablename__ = "users"

    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)

    # Role-based access control
    role_name: str = Field(
        sa_column=sa.Column("role", sa.String, nullable=False, server_default="user")
    )

    tier_name: str = Field(
        sa_column=sa.Column("tier", sa.String, nullable=False, server_default="free")
    )

    # Timestamps
    last_login: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )

    # Relationships
    documents: list["Document"] = Relationship(back_populates="owner")
    queries: list["Query"] = Relationship(back_populates="user")

    @property
    def role(self) -> UserRole:
        """Dynamically converts the string from the DB into the UserRole enum."""
        return UserRole(self.role_name)

    @role.setter
    def role(self, value: UserRole):
        """Allows setting the role using the Enum."""
        self.role_name = str(value)

    @property
    def tier(self) -> UserTier:
        """Dynamically converts the string from the DB into the UserTier enum."""
        return UserTier(self.tier_name)

    @tier.setter
    def tier(self, value: UserTier):
        """Allows setting the tier using the Enum."""
        self.tier_name = str(value)
