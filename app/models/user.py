from datetime import datetime

from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.models import Document


class User(SQLModel, table=True):
    """User database model."""

    __tablename__ = "users"

    id: int = Field(primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships/Ownership
    documents: list["Document"] = Relationship(back_populates="owner")
