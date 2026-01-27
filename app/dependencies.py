from typing import Annotated

from fastapi import Depends, Path, Query, Request, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session, redis_service, token_manager
from app.exceptions import (
    CredentialsException,
    DocumentNotFoundException,
    InactiveUserException,
    InsufficientScopesException,
    NotAuthorizedDocumenAccessException,
    RequiresRoleException,
    UserNotFoundException,
)
from app.models import Document, User
from app.schemas import PaginationParams
from app.services import StorageAdapter

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scopes={
        "read": "Read access to resources",
        "write": "Write access to resources",
        "admin": "Admin access to all resources",
        "moderate": "Moderate content",
    },
)


# Dependency for protected routes with scopes support
async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get the current authenticated user from token and verify scopes."""
    # Check if token is blacklisted
    if await redis_service.is_token_blacklisted(token):
        raise CredentialsException()

    # Decode token
    payload = token_manager.decode_token(token)
    if payload is None:
        raise CredentialsException()

    username: str | None = payload.get("sub")
    if username is None:
        raise CredentialsException()

    # Get token scopes
    token_scopes = payload.get("scopes", [])

    # Verify required scopes
    if security_scopes.scopes:
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise InsufficientScopesException(
                    required_scopes=security_scopes.scopes,
                    provided_scopes=token_scopes,
                )

    # Get user from database
    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        raise UserNotFoundException()

    if not user.is_active:
        raise InactiveUserException()

    return user


# Simplified version for endpoints that don't need scope checking
async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get the current authenticated user without scope verification."""
    # Check if token is blacklisted
    if await redis_service.is_token_blacklisted(token):
        raise CredentialsException()

    # Decode token
    payload = token_manager.decode_token(token)
    if payload is None:
        raise CredentialsException()

    username: str | None = payload.get("sub")
    if username is None:
        raise CredentialsException()

    # Get user from database
    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        raise UserNotFoundException()

    if not user.is_active:
        raise InactiveUserException()

    return user


# Admin-only user dependency
async def get_admin_user(
    current_user: User = Security(get_current_user, scopes=["admin"]),
) -> User:
    """Dependency that requires admin role and admin scope."""
    if current_user.role != "admin":
        raise RequiresRoleException("admin")
    return current_user


async def verify_document_ownership(
    document_id: Annotated[int, Path()],  # Explicitly from path
    current_user: User = Security(get_current_user, scopes=["read"]),
    session: AsyncSession = Depends(get_session),
) -> Document:
    """
    Dependency to verify that the current user owns the document or has admin access.

    Args:
        document_id: Document ID from path parameter
        current_user: Current authenticated user with 'read' scope
        session: Database session

    Raises:
        DocumentNotFoundException: If document doesn't exist
        NotAuthorizedDocumenAccessException: If user doesn't own the document

    Returns:
        Document: The document if user is the owner or admin
    """
    statement = select(Document).where(Document.id == document_id)
    result = await session.execute(statement)
    document = result.scalar_one_or_none()

    if not document:
        raise DocumentNotFoundException()

    # Admin users can access all documents
    if current_user.role == "admin":
        return document

    # Regular users can only access their own documents
    if document.owner_id != current_user.id:
        raise NotAuthorizedDocumenAccessException()

    return document


# Role-based access control
def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin/users", dependencies=[Depends(require_role("admin"))])
        async def list_all_users(): ...
    """

    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role:
            raise RequiresRoleException(required_role)
        return current_user

    return role_checker


# pagination
def pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """Dependency for pagination parameters"""
    return PaginationParams(page=page, page_size=page_size)


# MinIO Storage Service dependencies
def get_storage_service(request: Request) -> StorageAdapter:
    """Get storage service from app state."""
    return request.app.state.storage
