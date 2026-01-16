from datetime import datetime

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema with common attributes."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    pass


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

    class Config:
        from_attributes = True
