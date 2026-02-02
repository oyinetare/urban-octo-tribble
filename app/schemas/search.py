from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request schema for semantic search"""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    document_id: int | None = Field(
        None, description="Optional: Filter results to specific document"
    )
    limit: int = Field(5, ge=1, le=50, description="Maximum number of results to return")
    score_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    )
    mode: str = Field(
        "hybrid",
        description="Search mode: 'hybrid' (vector+keyword), 'vector' (semantic only), 'keyword' (full-text only)",
        pattern="^(hybrid|vector|keyword)$",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the main findings about climate change?",
                "document_id": None,
                "limit": 5,
                "score_threshold": 0.7,
                "mode": "hybrid",
            }
        }


class SearchResult(BaseModel):
    """Individual search result"""

    chunk_text: str = Field(..., description="Text content of the matching chunk")
    document_id: int = Field(..., description="ID of the document containing this chunk")
    chunk_index: int = Field(..., description="Position of chunk within document")
    score: float = Field(..., description="Similarity score (0-1, higher is better)")
    metadata: dict = Field(
        default_factory=dict, description="Additional metadata about the document"
    )
    # Optional scores for hybrid search transparency
    vector_score: float | None = Field(None, description="Vector similarity score (if applicable)")
    keyword_score: float | None = Field(None, description="Keyword relevance score (if applicable)")
    rrf_score: float | None = Field(None, description="RRF combined score (if applicable)")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_text": "Climate change is causing significant impacts...",
                "document_id": 123,
                "chunk_index": 5,
                "score": 0.89,
                "metadata": {
                    "document_title": "Climate Report 2024",
                    "document_filename": "climate_report.pdf",
                },
                "vector_score": 0.85,
                "keyword_score": 0.92,
                "rrf_score": 0.0327,
            }
        }


class SearchResponse(BaseModel):
    """Response schema for semantic search"""

    query: str = Field(..., description="Original search query")
    results: list[SearchResult] = Field(..., description="List of matching chunks")
    total_results: int = Field(..., description="Number of results returned")
    mode: str = Field(..., description="Search mode used")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "climate change impacts",
                "results": [
                    {
                        "chunk_text": "Climate change is causing significant impacts...",
                        "document_id": 123,
                        "chunk_index": 5,
                        "score": 0.89,
                        "metadata": {"document_title": "Climate Report 2024"},
                    }
                ],
                "total_results": 1,
                "mode": "hybrid",
            }
        }
