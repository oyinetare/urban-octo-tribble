from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import BigInteger
from sqlmodel import Field, Relationship

from app.core import ProcessingStatus
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
    description: str | None = Field(default=None, max_length=1000)
    content: str | None = Field(default=None)

    # File storage
    filename: str = Field(max_length=255)
    storage_key: str = Field(max_length=500)  # Path/key/file_path in MinIO
    file_size: int  # Size in bytes
    # mime_type
    content_type: str = Field(max_length=100)

    # Phase 2: Processing status
    processing_status: str = Field(
        sa_column=sa.Column(
            "status",
            sa.String,
            nullable=False,
            server_default="pending",
        ),
        description="Status: pending, processing, completed, failed",
    )
    processing_error: str | None = Field(default=None, max_length=1000)

    # Relationships/Ownership
    owner_id: int = Field(
        foreign_key="users.id",
        index=True,
        sa_type=BigInteger,
    )
    owner: "User" = Relationship(back_populates="documents")
    shorturls: list["ShortURL"] = Relationship(back_populates="document")

    @property
    def status(self) -> ProcessingStatus:
        """Dynamically converts the string from the DB into the ProcessingStatus enum."""
        return ProcessingStatus(self.processing_status)

    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"
