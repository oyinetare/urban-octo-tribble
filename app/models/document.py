from datetime import datetime

from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.models import User


class Document(SQLModel, table=True):
    """Document database model."""

    __tablename__ = "documents"

    id: int = Field(primary_key=True)
    title: str = Field(max_length=255)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships/Ownership
    owner_id: str = Field(
        foreign_key="users.id",
        index=True,
    )
    owner: "User" = Relationship(back_populates="document")

    def __repr__(self):
        return f"<Document {self.id}: {self.title}"
