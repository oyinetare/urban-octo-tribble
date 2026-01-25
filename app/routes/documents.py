from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core import SortOrder, get_session
from app.dependencies import (
    get_current_user,
    pagination_params,
    verify_document_ownership,
)
from app.exceptions import AppException
from app.models import Document, ShortURL, User
from app.schemas import (
    DocumentCreate,
    DocumentFilterParams,
    DocumentResponse,
    DocumentUpdate,
    PaginatedResponse,
    PaginationParams,
    ShortenResponse,
    StatsResponse,
)
from app.services import validator
from app.utility import base62_encoder, id_generator

router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Document:
    """
    Create a new document (protected endpoint).

    Supports idempotency via Idempotency-Key header.
    """
    document = Document(
        title=document_data.title,
        description=document_data.description,
        owner_id=current_user.id,
        shorturls=[],  # Initialize empty list
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    return document


@router.post("/upload")
async def upload_document(file: UploadFile):
    # Validate
    valid, message = await validator.validate(file)
    if not valid:
        raise AppException(message)


@router.get("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_document(document: Document = Depends(verify_document_ownership)) -> Document:
    """
    Get a document by ID.
    Only returns document if current user is the owner.
    """
    return document


@router.put("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
async def update_document(
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
):
    """
    Delete a document (idempotent by design).
    Only owner can delete.
    """
    await session.delete(document)
    await session.commit()


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
    "/share/{document_id}", status_code=status.HTTP_201_CREATED, response_model=ShortenResponse
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
