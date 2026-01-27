from datetime import datetime

from fastapi import Form, Query
from pydantic import BaseModel, Field

from app.core import ProcessingStatus, SortOrder


class DocumentBase(BaseModel):
    """Base document schema with common attributes."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


# Only use a Pydantic model for the entire request if you are not uploading a file and only sending text-based data as a JSON object. If your project specifically requires a model-based approach for forms, you can use:
class DocumentCreate(BaseModel):
    title: str
    description: str | None = None

    @classmethod
    def as_form(
        cls,
        # Use ... to mark it as required in the Form
        title: str = Form(..., min_length=1, max_length=255),
        description: str | None = Form(default=None, max_length=1000),
    ):
        return cls(title=title, description=description)


class DocumentUpdate(BaseModel):
    """Schema for creating a new document."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class DocumentResponse(BaseModel):
    """Schema for document responses."""

    id: int
    title: str
    description: str
    owner_id: int
    created_at: datetime
    processing_status: ProcessingStatus
    processing_error: str | None = None

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
    processing_status: ProcessingStatus
    processing_error: str | None = None
    task_id: str | None = None


class DocumentDownloadResponse(BaseModel):
    """Schema for response after successful file/document download."""

    download_url: str
    expires_in_seconds: int = 3600


class ProcessingStatusResponse(BaseModel):
    """Schema for checking processing status."""

    document_id: int
    status: ProcessingStatus
    error: str | None = None
    # task_id: str | None = None
    # task_state: str | None = None
    # task_result: dict | None = None
