from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models import User


class Document(SQLModel, table=True):
    """Document database model."""

    __tablename__ = "documents"

    id: int = Field(primary_key=True)

    # Document metadata
    title: str = Field(max_length=255, index=True)
    # filename: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships/Ownership
    owner_id: int = Field(
        foreign_key="users.id",
        index=True,
    )
    owner: "User" = Relationship(back_populates="documents")

    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"
