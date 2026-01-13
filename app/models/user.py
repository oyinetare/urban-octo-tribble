from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

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

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    documents: list["Document"] = Relationship(back_populates="owner")
