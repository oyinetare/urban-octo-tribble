from datetime import datetime

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request schema for asking questions."""

    query: str = Field(..., min_length=1, max_length=1000, description="Question to ask")
    document_id: int | None = Field(
        default=None, description="Specific document ID (None = search all user's documents)"
    )
    max_chunks: int = Field(default=5, ge=1, le=10, description="Maximum context chunks to use")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum similarity score")


class Citation(BaseModel):
    """Citation information for a source chunk."""

    chunk_id: int | None = Field(None, description="Chunk ID")
    document_id: int = Field(..., description="Document ID")
    document_title: str = Field(..., description="Document title")
    chunk_position: int = Field(..., description="Position in document")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    text_preview: str = Field(..., description="Preview of chunk text")


class QueryResponse(BaseModel):
    """Response schema for query results."""

    query: str = Field(..., description="Original question")
    answer: str = Field(..., description="AI-generated answer")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
    llm_provider: str = Field(..., description="LLM provider used")
    llm_model: str = Field(..., description="Model used")
    tokens_used: int | None = Field(default=None, description="Tokens consumed")
    response_time_ms: int = Field(..., description="Response time in milliseconds")


class QueryHistoryResponse(BaseModel):
    """Response schema for query history."""

    id: int
    query: str
    answer: str
    document_id: int | None
    chunks_used: list[int]
    llm_provider: str
    llm_model: str
    tokens_used: int | None
    response_time_ms: int | None
    created_at: datetime

    class Config:
        from_attributes = True
