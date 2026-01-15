from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

from app.core import UserRole

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models import Document


class User(SQLModel, table=True):
    """User database model."""

    __tablename__ = "users"

    id: int = Field(primary_key=True)

    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)

    # Role-based access control
    role_name: str = Field(
        sa_column=sa.Column("role", sa.String, nullable=False, server_default="user")
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: datetime = Field(default_factory=datetime.now)

    # Relationships
    documents: list["Document"] = Relationship(back_populates="owner")

    @property
    def role(self) -> UserRole:
        """Dynamically converts the string from the DB into the UserRole enum."""
        return UserRole(self.role_name)

    @role.setter
    def role(self, value: UserRole):
        """Allows setting the role using the Enum."""
        self.role_name = str(value)
