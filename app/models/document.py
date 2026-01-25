from typing import TYPE_CHECKING

from sqlalchemy import BigInteger
from sqlmodel import Field, Relationship

from app.models import BaseModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models import ShortURL, User


class Document(BaseModel, table=True):
    """Document database model."""

    __tablename__ = "documents"

    # Document metadata
    title: str = Field(max_length=255, index=True)

    # Document metadata
    title: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None, max_length=1000)

    # File storage
    # filename: str = Field(max_length=255)
    # storage_key: str = Field(max_length=500)  # Path/key in MinIO
    # file_size: int  # Size in bytes
    # content_type: str = Field(max_length=100)

    # Relationships/Ownership
    owner_id: int = Field(
        foreign_key="users.id",
        index=True,
        sa_type=BigInteger,
    )
    owner: "User" = Relationship(back_populates="documents")
    shorturls: list["ShortURL"] = Relationship(back_populates="document")

    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"
