from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session, redis_service, token_manager
from app.exceptions import (
    CredentialsException,
    InactiveUserException,
    InsufficientScopesException,
    UserNotFoundException,
)
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
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
