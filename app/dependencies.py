from typing import Annotated

from fastapi import Depends, Path, Query, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session, services, token_manager
from app.exceptions import (
    CredentialsException,
    DocumentNotFoundException,
    InactiveUserException,
    InsufficientScopesException,
    NotAuthorizedDocumenAccessException,
    RequiresRoleException,
    UserNotFoundException,
)
from app.models.document import Document
from app.models.user import User
from app.schemas import PaginationParams
from app.services.embeddings import EmbeddingService
from app.services.hybrid_search import HybridSearchService
from app.services.llm import LLMService
from app.services.rag import RAGService
from app.services.redis_service import RedisService
from app.services.vector_store import VectorStoreService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scopes={
        "read": "Read access to resources",
        "write": "Write access to resources",
        "admin": "Admin access to all resources",
        "moderate": "Moderate content",
    },
)

# Service dependencies


async def get_redis_service():
    """Get the initialized Redis service from the container."""
    if not services.redis:
        await services.init()
    return services.redis


async def get_embedding_service():
    """Get the initialized Embedding service from the container."""
    if not services.embedding:
        await services.init()
    return services.embedding


async def get_vector_service():
    """Get the initialized Vector Store service from the container."""
    if not services.vector_store:
        await services.init()
    return services.vector_store


# MinIO Storage Service dependencies
async def get_storage_service():
    """Get storage service from app state.
    Get the initialized Storage service from the container.
    If inside a FastAPI request, get from app.state (better for testing/overrides).
    If called without a request (Celery), return the global instance.
    """
    if not services.storage:
        await services.init()
    return services.storage


async def get_services():
    """Returns the full initialized service container."""
    if not (services.redis and services.storage):
        await services.init()
    return services


async def get_llm_service() -> LLMService:
    """Dependency to get LLM service."""
    return LLMService()


async def get_rag_service(
    vector_store: VectorStoreService = Depends(get_vector_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
) -> RAGService:
    """
    Dependency to get RAG service with production optimizations.

    This creates a new RAGService instance per request but includes
    the shared Redis, metrics, and classifier services for caching
    and performance tracking.
    """
    # Ensure services are initialized
    if not services.redis or not services.metrics or not services.classifier:
        await services.init()

    return RAGService(
        vector_store=vector_store,
        llm_service=llm_service,
        embedding_service=embedding_service,
        session=session,
        # ✅ Add optimization services
        redis=services.redis,
        metrics_service=services.metrics,
        classifier=services.classifier,
    )


async def get_hybrid_search_service(
    vector_store: VectorStoreService = Depends(get_vector_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    session: AsyncSession = Depends(get_session),
) -> HybridSearchService:
    """
    Get hybrid search service instance.

    Dependencies:
        - Vector store for semantic search
        - Embedding service for query embeddings
        - Database session for full-text search
    """
    return HybridSearchService(
        vector_store=vector_store,
        embedding_service=embedding_service,
        session=session,
    )


#########


# Dependency for protected routes with scopes support
async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
    redis: RedisService = Depends(get_redis_service),
) -> User:
    """Get the current authenticated user from token and verify scopes."""
    # Check if token is blacklisted
    if await redis.is_token_blacklisted(token):
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
    redis: RedisService = Depends(get_redis_service),
) -> User:
    """Get the current authenticated user without scope verification."""
    # Check if token is blacklisted
    if await redis.is_token_blacklisted(token):
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
