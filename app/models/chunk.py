from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Index
from sqlmodel import Field, Relationship

from app.models import BaseModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models.document import Document


class Chunk(BaseModel, table=True):
    """Document chunk database model."""

    text: str = Field(description="The content of the chunk")
    position: int = Field(index=True, description="The sequence order within the document")
    tokens: int = Field(description="Token count for this chunk")
    embedding_id: str | None = Field(default=None, description="Reference to the vector embedding")

    document_id: int = Field(
        foreign_key="documents.id",
        index=True,
        sa_type=BigInteger,
    )

    # Updated back_populates to reflect the list of chunks on Document
    document: "Document" = Relationship(back_populates="chunks")

    # composite index if you often query by document and position together
    __table_args__ = (Index("ix_chunk_document_id_position", "document_id", "position"),)
