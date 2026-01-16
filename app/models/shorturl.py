from typing import TYPE_CHECKING

from sqlalchemy import BigInteger
from sqlmodel import Field, Relationship

from app.models import BaseModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models.document import Document


class ShortURL(BaseModel, table=True):
    """ShortURL database model."""

    __tablename__ = "shorturls"

    # 11 is the mathematical minimum for Snowflake IDs in Base62
    short_code: str = Field(max_length=11, unique=True, index=True)

    document_id: int = Field(
        foreign_key="documents.id",
        index=True,
        sa_type=BigInteger,
    )
    document: "Document" = Relationship(back_populates="shorturls")

    clicks: int = Field(default=0)

    def __repr__(self):
        return f"<ShortURL {self.short_code}: clicks={self.clicks}>"
