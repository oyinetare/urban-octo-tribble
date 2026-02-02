from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import BigInteger
from sqlmodel import Field, Relationship

from app.core import ProcessingStatus
from app.models.base import BaseModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.query import Query
    from app.models.shorturl import ShortURL
    from app.models.user import User


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
    task_id: str | None = Field(default=None)

    # Relationships/Ownership
    owner_id: int = Field(
        foreign_key="users.id",
        index=True,
        sa_type=BigInteger,
    )
    owner: "User" = Relationship(back_populates="documents")
    shorturls: list["ShortURL"] = Relationship(back_populates="document")
    chunks: list["Chunk"] = Relationship(
        back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    queries: list["Query"] = Relationship(back_populates="document")

    @property
    def status(self) -> ProcessingStatus:
        return ProcessingStatus(self.processing_status)

    @status.setter
    def status(self, value: ProcessingStatus):
        self.processing_status = value.value

    def __repr__(self):
        return f"<Document {self.id}: {self.title}>"
