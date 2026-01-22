from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, Field

from app.core import SortOrder


class DocumentBase(BaseModel):
    """Base document schema with common attributes."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class DocumentUpdate(BaseModel):
    """Schema for creating a new document."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class DocumentResponse(BaseModel):
    """Schema for document responses."""

    id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentFilterParams:
    """Filter and sort parameters for documents"""

    def __init__(
        self,
        search: str | None = Query(None, description="Search in title/content"),
        sort_by: str | None = Query("created_at", description="Field to sort by"),
        sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    ):
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


class DocumentUploadResponse(BaseModel):
    """Schema for response after successful file/document upload."""

    id: int
    title: str
    filename: str
    file_size: int
    content_type: str
    storage_key: str
