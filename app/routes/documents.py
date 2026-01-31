import logging

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.celery_app import celery_app
from app.core import ProcessingStatus, SortOrder, get_session
from app.dependencies import (
    get_current_user,
    get_storage_service,
    get_vector_service,
    pagination_params,
    verify_document_ownership,
)
from app.exceptions import AppException, InvalidFileException
from app.models import Document, ShortURL, User
from app.schemas import (
    DocumentCreate,
    DocumentDownloadResponse,
    DocumentFilterParams,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
    PaginatedResponse,
    PaginationParams,
    ShortenResponse,
    StatsResponse,
)
from app.schemas.document import ProcessingStatusResponse
from app.services.storage import StorageAdapter
from app.services.validators import validator
from app.services.vector_store import VectorStoreService
from app.utility import base62_encoder, id_generator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, deprecated=True
)
async def create_document(
    document_metadata: DocumentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Document:
    """
    Create a new document (protected endpoint).

    Supports idempotency via Idempotency-Key header.
    """
    document = Document(
        title=document_metadata.title,
        description=document_metadata.description,
        filename="",
        storage_key="",
        file_size=0,
        content_type="application/octet-stream",
        owner_id=current_user.id,
        processing_status=ProcessingStatus.PENDING,
    )

    try:
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document
    except Exception as e:
        await session.rollback()
        # Re-raise as AppException to handle it outside the TaskGroup
        raise AppException(status_code=500, message=f"DB Error: {str(e)}") from e


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_metadata: DocumentCreate = Depends(DocumentCreate.as_form),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    storage: StorageAdapter = Depends(get_storage_service),
):
    # 1. Early exit if file is missing (prevents validator crashes)
    if not file or not file.filename:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, message="No file uploaded"
        )

    # 2. Validate using your chain
    valid, message = await validator.validate(file)
    if not valid:
        raise InvalidFileException(message)

    # 3. Efficiently get size without loading everything into RAM
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    try:
        # Use the SpooledTemporaryFile directly instead of re-wrapping in BytesIO
        storage_key = await storage.upload(
            file_data=file.file,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            user_id=current_user.id,
        )

        # Create database record
        document = Document(
            title=document_metadata.title,
            description=document_metadata.description,
            filename=file.filename,
            storage_key=storage_key,
            file_size=file_size,
            content_type=file.content_type,
            owner_id=current_user.id,
            processing_status=ProcessingStatus.PENDING,
        )

        session.add(document)
        await session.commit()
        await session.refresh(document)

        # Trigger background processing
        from app.tasks import process_document

        task = process_document.apply_async(args=[document.id])

        document.task_id = task.id
        await session.commit()

        return DocumentUploadResponse(
            id=document.id,
            title=document.title,
            filename=document.filename,
            file_size=document.file_size,
            content_type=document.content_type,
            storage_key=document.storage_key,
            # task tracking
            processing_status=ProcessingStatus.PROCESSING,
            task_id=task.id,
        )

    except Exception as e:
        await session.rollback()
        # catching general Exception and re-raising as AppException is standard to avoid leaking TaskGroup details to the client.
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Upload failed: {str(e)}",
        ) from e


@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
async def get_document_file(
    document: Document = Depends(verify_document_ownership),
    storage: StorageAdapter = Depends(get_storage_service),
):
    """
    Generate a presigned download URL for a document.
    """
    # Generate presigned URL
    download_url = await storage.get_presigned_url(object_key=document.storage_key)

    return DocumentDownloadResponse(download_url=download_url)


@router.get("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_document_metadata(document: Document = Depends(verify_document_ownership)) -> Document:
    """
    Get a document by ID.
    Only returns document if current user is the owner.
    """
    return document


@router.put("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
async def update_document_metadata(
    document_data: DocumentUpdate,
    document: Document = Depends(verify_document_ownership),
    session: AsyncSession = Depends(get_session),
    # storage: MinIOAdapter = Depends(get_storage_service),
) -> Document:
    """
    Update a document (idempotent by design).
    Only owner can update.
    """
    # Use exclude_unset=True so only fields in the request body are updated
    update_data = document_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(document, key, value)

    session.add(document)
    await session.commit()
    await session.refresh(document)

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: Document = Depends(verify_document_ownership),
    session: AsyncSession = Depends(get_session),
    storage: StorageAdapter = Depends(get_storage_service),
    vector_store: VectorStoreService = Depends(get_vector_service),
):
    """
    Delete a document (idempotent by design).
    Only owner can delete.
    """
    # 1. Clean up Vector Store (Embeddings)
    try:
        await vector_store.delete_document(document.id)
    except Exception as e:
        logger.error(f"Vector delete failed for {document.id}: {e}")

    # 2. Clean up Storage (Physical File)
    try:
        await storage.delete(document.storage_key)
    except Exception as e:
        logger.warning(f"Storage delete failed for {document.storage_key}: {e}")

    # 3. Final Database removal
    try:
        await session.delete(document)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Database error: {str(e)}",
        ) from e

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=PaginatedResponse[DocumentResponse], status_code=status.HTTP_200_OK)
async def list_user_documents(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    pagination: PaginationParams = Depends(pagination_params),
    filters: DocumentFilterParams = Depends(),
) -> PaginatedResponse[DocumentResponse]:
    """
    List all documents owned by current user with pagination, filtering, and sorting.

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - search: Search in title/description
    - sort_by: Field to sort by (default: created_at)
    - sort_order: asc or desc (default: desc)
    """
    # Base query
    statement = select(Document).where(Document.owner_id == current_user.id)

    # Apply search filter
    if filters.search:
        search_term = f"%{filters.search}%"
        statement = statement.where(
            (col(Document.title).ilike(search_term))
            | (col(Document.description).ilike(search_term))
        )

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total_result = await session.execute(count_statement)
    total = total_result.scalar_one()

    # Apply sorting
    if filters.sort_by:
        sort_column = getattr(Document, filters.sort_by, None)
        if sort_column is not None:
            if filters.sort_order == SortOrder.DESC:
                statement = statement.order_by(sort_column.desc())
            else:
                statement = statement.order_by(sort_column.asc())

    # Apply pagination
    statement = statement.offset(pagination.skip).limit(pagination.limit)

    # Execute query
    result = await session.execute(statement)
    documents = result.scalars().all()

    return PaginatedResponse.create(items=list(documents), total=total, pagination=pagination)


@router.get("/{short_code}/stats", response_model=StatsResponse)
async def get_short_url_stats(
    short_code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get analytics for a short URL."""
    statement = select(ShortURL).where(ShortURL.short_code == short_code)
    result = await session.execute(statement)
    short_url = result.scalar_one_or_none()

    if not short_url:
        raise AppException(status_code=status.HTTP_404_NOT_FOUND, message="Short URL not found")

    return StatsResponse(
        short_code=short_url.short_code,
        document_id=short_url.document_id,
        clicks=short_url.clicks,
        created_at=short_url.created_at.isoformat(),
    )


# === SHORTEN ===
@router.post(
    "/{document_id}/share", status_code=status.HTTP_201_CREATED, response_model=ShortenResponse
)
async def create_short_url(
    document: Document = Depends(verify_document_ownership),
    session: AsyncSession = Depends(get_session),
):
    """Share by creating a short URL for a document."""

    # Check if short URL already exists for this document
    existing = await session.execute(select(ShortURL).where(ShortURL.document_id == document.id))
    existing_url = existing.scalar_one_or_none()

    if existing_url:
        # Return existing short URL instead of creating duplicate
        return ShortenResponse(
            short_code=existing_url.short_code,
            document_id=existing_url.document_id,
            clicks=existing_url.clicks,
            original_url=f"/api/v1/documents/{document.id}",
            short_url=f"/d/{existing_url.short_code}",
        )

    # Generate unique ID and encode
    unique_id = id_generator.generate()
    short_code = base62_encoder.encode(unique_id)

    # Create NEW short URL (only once!)
    short_url = ShortURL(short_code=short_code, document_id=document.id, clicks=0)

    session.add(short_url)
    await session.commit()
    await session.refresh(short_url)

    return ShortenResponse(
        short_code=short_url.short_code,
        document_id=short_url.document_id,
        clicks=short_url.clicks,
        original_url=f"/api/v1/documents/{document.id}",
        short_url=f"/d/{short_url.short_code}",
    )


# === REDIRECT ===


# Redirect endpoint (separate from /shorten prefix)
# This should be registered directly on the app with a different router
redirect_router = APIRouter(tags=["Documents"])


@redirect_router.get("/d/{short_code}")
async def redirect_short_url(short_code: str, session: AsyncSession = Depends(get_session)):
    """Redirect a short URL to the original document."""
    # Look up short URL
    statement = select(ShortURL).where(ShortURL.short_code == short_code)
    result = await session.execute(statement)
    short_url = result.scalar_one_or_none()

    if not short_url:
        raise AppException(status_code=status.HTTP_404_NOT_FOUND, message="Short URL not found")

    # Increment click count
    short_url.clicks += 1
    await session.commit()

    # Redirect to original URL
    original_url = f"/documents/{short_url.document_id}"
    return RedirectResponse(url=original_url, status_code=301)


# === PROCESSING ===


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    document: Document = Depends(verify_document_ownership),
):
    """
    Get the processing status of a document.

    Status values:
    - "pending": Waiting to be processed
    - "processing": Currently being processed by Celery worker
    - "completed": Ready for queries and summarization
    - "failed": Processing failed (check error field)

    Example:
        GET /documents/1/status

    Returns:
        {
            "document_id": 1,
            "status": "completed",
            "error": null
        }
    """
    progress = 0

    # 1. If it's already completed in DB, it's 100%
    if document.status == ProcessingStatus.COMPLETED:
        progress = 100

    # 2. If it's processing, check Celery for the 'PROGRESS' state we set in the task
    elif document.task_id:
        result = AsyncResult(document.task_id, app=celery_app)
        if result.state == "PROGRESS":
            # This 'percent' comes from your self.update_state call in the task
            progress = result.info.get("percent", 0)
        elif result.state == "SUCCESS":
            progress = 100
        elif result.state == "FAILURE":
            progress = 0

    return ProcessingStatusResponse(
        document_id=document.id,
        status=document.status,
        progress=progress,
        error=document.processing_error,
        task_id=document.task_id,  # Now this will be populated
    )
