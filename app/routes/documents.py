from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session
from app.dependencies import get_current_user, verify_document_ownership
from app.models import Document, User
from app.schemas import DocumentCreate, DocumentResponse
from app.schemas.document import DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Create a new document (protected endpoint)."""
    document = Document(**document_data.model_dump(), owner_id=current_user.id)

    session.add(document)
    await session.commit()
    await session.refresh(document)

    return document


@router.get("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_document(document: Document = Depends(verify_document_ownership)) -> Document:
    """
    Get a document by ID.
    Only returns document if current user is the owner.
    """
    return document


@router.put(
    "/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK
)  # Changed to 200 OK for updates
async def update_document(
    document_data: DocumentUpdate,
    document: Document = Depends(verify_document_ownership),
    session: AsyncSession = Depends(get_session),
) -> Document:
    """
    Update a document.
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
