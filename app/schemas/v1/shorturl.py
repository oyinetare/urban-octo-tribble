from pydantic import BaseModel


class ShortenResponse(BaseModel):
    """Response schema for short URL."""

    short_code: str
    document_id: int
    clicks: int
    original_url: str
    short_url: str


class StatsResponse(BaseModel):
    """Response schema for short URL statistics."""

    short_code: str
    document_id: int
    clicks: int
    created_at: str
