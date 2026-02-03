from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, Column
from sqlmodel import Field, Relationship

from app.models.base import BaseModel

# This import only happens during type checking, not at runtime
# standard Python pattern for avoiding circular imports while keeping type checkers happy
if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class Query(BaseModel, table=True):
    """Query history for RAG system."""

    __tablename__ = "queries"

    # Foreign Keys
    user_id: int = Field(
        foreign_key="users.id",
        index=True,
        sa_type=BigInteger,
    )
    document_id: int | None = Field(
        default=None,
        foreign_key="documents.id",
        index=True,
        nullable=True,
        sa_type=BigInteger,
    )

    # Query Details
    query: str = Field(..., description="User's question")
    answer: str = Field(..., description="AI-generated answer")

    # Metadata
    chunks_used: list[int] = Field(
        default_factory=list, sa_column=Column(JSON), description="Chunk IDs used in context"
    )
    llm_provider: str = Field(..., description="LLM provider used (anthropic/ollama)")
    llm_model: str = Field(..., description="Specific model used")
    tokens_used: int | None = Field(default=None, description="Total tokens consumed")
    response_time_ms: int | None = Field(default=None, description="Response time in milliseconds")

    # Relationships
    user: "User" = Relationship(back_populates="queries")
    document: "Document" = Relationship(back_populates="queries")

    class Config:
        arbitrary_types_allowed = True
