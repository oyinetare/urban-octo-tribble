from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session
from app.core.notification import NotificationService
from app.dependencies import (
    get_current_active_user,
    get_current_user,
    get_notification_service,
    verify_document_ownership,
)
from app.exceptions import AppException
from app.models import Document, Notification, ShortURL, User
from app.schemas import DocumentCreate, DocumentResponse, ShortenResponse, StatsResponse
from app.schemas.document import DocumentUpdate
from app.utils import generate_short_code

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("")
async def create_document(
    document_data: DocumentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Create a new document with notification."""
    # Create document
    document = Document(**document_data.model_dump(), owner_id=current_user.id)

    session.add(document)
    await session.commit()
    await session.refresh(document)

    # Create notification
    notification = Notification(
        user_id=current_user.id,
        type="document_uploaded",
        title="Document Uploaded",
        message=f"Your document '{document.title}' has been uploaded successfully",
        action_url=f"/documents/{document.id}",
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    #  Trigger notification delivery (webhook, email, etc.)
    # This enqueues tasks and returns immediately (~1ms)
    await notification_service.notify(notification)

    return {
        "success": True,
        "document": {
            "id": document.id,
            "title": document.title,
            "description": document.description,
            "created_at": document.created_at.isoformat(),
        },
        "notification_sent": True,
    }


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
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Update a document and send notification.

    Only owner can update.
    Sends notification on update.
    """
    # Use exclude_unset=True so only fields in the request body are updated
    update_data = document_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(document, key, value)

    session.add(document)
    await session.commit()
    await session.refresh(document)

    # Send notification on update
    notification = Notification(
        user_id=document.owner_id,
        type="document_updated",
        title="Document Updated",
        message=f"Your document '{document.title}' has been updated",
        action_url=f"/documents/{document.id}",
    )
    session.add(notification)
    await session.commit()
    await notification_service.notify(notification)

    return {
        "success": True,
        "document": {
            "id": document.id,
            "title": document.title,
            "description": document.description,
            "updated_at": document.updated_at.isoformat(),
        },
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: Document = Depends(verify_document_ownership),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a document.
    Only owner can delete.
    """
    await session.delete(document)
    await session.commit()


@router.get("/", response_model=list[DocumentResponse], status_code=status.HTTP_200_OK)
async def list_user_documents(
    current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[Document]:
    """
    List all documents owned by current user.
    """
    statement = select(Document).where(Document.owner_id == current_user.id)
    result = await session.execute(statement)
    documents = result.scalars().all()

    return list(documents)


# === SHORTEN ===
@router.post(
    "/share/{document_id}", status_code=status.HTTP_201_CREATED, response_model=ShortenResponse
)
async def create_short_code_URL(
    document: Document = Depends(verify_document_ownership),
    session: AsyncSession = Depends(get_session),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Share by creating a short URL for a document with optional notification.
    """
    # Generate short code
    short_code = generate_short_code(document.id)

    # Check for collision
    statement = select(ShortURL).where(ShortURL.short_code == short_code)
    existing_result = await session.execute(statement)
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Handle collision - add random suffix
        import random

        from app.utils.url_shortener import Base62Encoder

        suffix = "".join(random.choices(Base62Encoder.ALPHABET, k=2))
        short_code = short_code[:5] + suffix  # Keep first 5 chars, add 2 random

    # Create short URL
    short_url = ShortURL(short_code=short_code, document_id=document.id, clicks=0)

    # Create short URL
    short_url = ShortURL(
        short_code=short_code,
        document_id=document.id,
        clicks=0,
    )
    session.add(short_url)
    await session.commit()
    await session.refresh(short_url)

    # Send notification when short URL is created
    notification = Notification(
        user_id=document.owner_id,
        type="short_url_created",
        title="Short URL Created",
        message=f"Short URL created for '{document.title}': /{short_code}",
        action_url=f"/d/{short_code}",
    )
    session.add(notification)
    await session.commit()
    await notification_service.notify(notification)

    return {
        "success": True,
        "short_url": {
            "short_code": short_code,
            "full_url": f"/d/{short_code}",
            "document_id": document.id,
            "clicks": 0,
        },
    }


@router.get("/{short_code}/stats", response_model=StatsResponse)
async def get_short_code_url_stats(
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


# === REDIRECT ===


# Redirect endpoint (separate from /shorten prefix)
# This should be registered directly on the app with a different router

redirect_router = APIRouter(tags=["redirect"])


@redirect_router.get("/d/{short_code}")
async def redirect_short_url(
    short_code: str,
    session: AsyncSession = Depends(get_session),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Redirect a short URL to the original document and send notification.

     Now sends notification when short URL is clicked.
    """

    # Get short URL with document relationship
    statement = select(ShortURL).where(ShortURL.short_code == short_code)
    result = await session.execute(statement)
    short_url = result.scalar_one_or_none()

    if not short_url:
        raise AppException(status_code=status.HTTP_404_NOT_FOUND, message="Short URL not found")

    # Load document relationship
    await session.refresh(short_url, ["document"])

    # Increment click counter
    short_url.clicks += 1
    session.add(short_url)

    #  Create notification for document owner
    notification = Notification(
        user_id=short_url.document.owner_id,
        type="short_url_clicked",
        title="Short URL Clicked",
        message=f"Your short URL /{short_code} was clicked (total: {short_url.clicks})",
        action_url=f"/documents/{short_url.document_id}/stats",
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    #  Trigger notification delivery
    # This happens in background, doesn't slow down redirect
    await notification_service.notify(notification)

    # Redirect to original document URL
    original_url = f"/documents/{short_url.document_id}"
    return RedirectResponse(url=original_url, status_code=301)
