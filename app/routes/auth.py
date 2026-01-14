from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session, redis_service, token_manager
from app.core.config import get_settings
from app.dependencies import oauth2_scheme
from app.exceptions import (
    AppException,
    CredentialsException,
    InactiveUserException,
    UserAlreadyExistsException,
)
from app.models import User
from app.schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session)) -> User:
    """Register a new user."""
    try:
        # Check if user already exists
        statement = select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
        result = await session.execute(statement)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsException()

        # Create new user with hashed password
        hashed_password = token_manager.get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role if user_data.role else "user",  # Default to "user" role
            # tier=user_data.tier if user_data.tier else "free",  # Default to "free" tier
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user

    except IntegrityError:
        await session.rollback()
        raise UserAlreadyExistsException() from None
    except Exception as e:
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"An error occurred: {str(e)}",
        ) from e


@router.post("/login")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Login and get access and refresh tokens with scopes."""
    # Find user by username
    statement = select(User).where(User.username == form_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    # Verify user and password
    if not user or not token_manager.verify_password_hash(form_data.password, user.hashed_password):
        raise CredentialsException()

    if not user.is_active:
        raise InactiveUserException()

    # Update last_login timestamp
    user.last_login = datetime.now()
    session.add(user)
    await session.commit()

    # Define scopes based on user role
    scopes = user.role.scopes
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = token_manager.create_token(
        data={"sub": user.username, "scopes": scopes}, expires_delta=access_token_expires
    )

    # refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # refresh_token = token_manager.create_refresh_token(
    #     data={"sub": user.username, "scopes": scopes}, expires_delta=refresh_token_expires
    # )

    # # Set refresh token in HttpOnly cookie for security
    # response.set_cookie(
    #     key="refresh_token",
    #     value=refresh_token,
    #     httponly=True,  # Prevents JavaScript access (XSS protection)
    #     secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
    #     samesite="lax",  # CSRF protection
    #     max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # seconds
    # )

    return Token(access_token=access_token, token_type="bearer", scopes=scopes)


@router.post("/refresh")
def refresh_access_token(response: Request, session: AsyncSession = Depends(get_session)):
    """Refresh the access token using the refresh token from cookie."""


@router.post("/logout")
async def logout(request: Request, response: Response, token: str = Depends(oauth2_scheme)):
    """Logout by blacklisting tokens and clearing cookies."""
    access_token_expiry = token_manager.get_token_expiry(token)
    if access_token_expiry:
        expires_in = int((access_token_expiry - datetime.now()).total_seconds())
        if expires_in > 0:
            await redis_service.blacklist_token(token, expires_in)

    return {"message": "Successfully logged out"}
