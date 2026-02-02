from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session, services, token_manager
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

router = APIRouter()
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

    # 1. Catch specific custom exceptions first (if you want to handle them here)
    except UserAlreadyExistsException:
        await session.rollback()
        raise  # Re-raise it so FastAPI can handle it with the correct status code

    # 2. Catch specific library errors
    except IntegrityError:
        await session.rollback()
        raise UserAlreadyExistsException() from None

    # 3. Finally, catch everything else as a 500
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

    user.last_login = datetime.now()
    session.add(user)
    await session.commit()

    # Access tier limit and user id for the token payload
    # This assumes User has a relationship to Tier
    tier_limit = user.tier.limit
    scopes = user.role.scopes

    # Use the new TokenManager signature
    access_token = token_manager.create_access_token(
        user_id=user.id, username=user.username, tier_limit=user.tier.limit, scopes=user.role.scopes
    )

    refresh_token = token_manager.create_refresh_token(
        data={"sub": user.username, "id": user.id, "tier_limit": tier_limit, "scopes": scopes}
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # seconds
    )

    return Token(access_token=access_token, token_type="bearer", scopes=scopes)


@router.post("/refresh")
async def refresh_access_token(request: Request, session: AsyncSession = Depends(get_session)):
    """Refresh the access token using the refresh token from cookie."""
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise CredentialsException()

    # TYPE SAFE REDIS CHECK
    redis = services.redis
    if redis and await redis.is_token_blacklisted(refresh_token):
        raise CredentialsException()

    payload = token_manager.decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise CredentialsException()

    username = payload.get("sub")
    if not username:
        raise CredentialsException()

    # Refresh user to ensure we have the latest tier/role
    statement = select(User).where(User.username == username)
    user = (await session.execute(statement)).scalar_one_or_none()

    if not user or not user.is_active:
        raise InactiveUserException()

    # Re-issue access token with updated claims
    access_token = token_manager.create_access_token(
        user_id=user.id, username=user.username, tier_limit=user.tier.limit, scopes=user.role.scopes
    )

    return Token(access_token=access_token, token_type="bearer", scopes=user.role.scopes)


@router.post("/logout")
async def logout(request: Request, response: Response, token: str = Depends(oauth2_scheme)):
    """Logout by blacklisting tokens and clearing cookies."""
    # Blacklist the access token
    redis = services.redis
    if not redis:
        return {"message": "Logout skipped: Cache unavailable"}

    now = datetime.now()

    # Blacklist Access Token
    access_expiry = token_manager.get_token_expiry(token)
    if access_expiry:
        diff = int((access_expiry - now).total_seconds())
        if diff > 0:
            await redis.blacklist_token(token, diff)

    # Blacklist Refresh Token
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        refresh_expiry = token_manager.get_token_expiry(refresh_token)
        if refresh_expiry:
            diff = int((refresh_expiry - now).total_seconds())
            if diff > 0:
                await redis.blacklist_token(refresh_token, diff)

    response.delete_cookie("refresh_token")
    return {"message": "Successfully logged out"}
