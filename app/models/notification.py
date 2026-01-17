from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime
from sqlmodel import Field, Relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import User


class Notification(BaseModel, table=True):
    """Notification database model."""

    __tablename__ = "notifications"

    # Notification type (document_uploaded, query_completed, etc.)
    type: str = Field(max_length=50, index=True)

    # Notification content
    title: str = Field(max_length=255)
    message: str = Field(max_length=1000)

    # Optional action URL (e.g., link to document)
    action_url: str | None = Field(default=None, max_length=500)

    # Read status
    read_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )

    # Relationships/Ownership
    user_id: int = Field(
        foreign_key="users.id",
        index=True,
        sa_type=BigInteger,
    )
    user: "User" = Relationship(back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id}: {self.type} for user {self.user_id}>"

    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None
