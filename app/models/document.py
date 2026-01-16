from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.models import BaseModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models import User


class Document(BaseModel, table=True):
    """Document database model."""

    __tablename__ = "documents"

    # Document metadata
    title: str = Field(max_length=255, index=True)
    # filename: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)

    # Timestamps

    # Relationships/Ownership
    owner_id: int = Field(
        foreign_key="users.id",
        index=True,
    )
    owner: "User" = Relationship(back_populates="documents")

    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"
