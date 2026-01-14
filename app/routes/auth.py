from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import get_session, token_manager
from app.exceptions import AppException, UserAlreadyExistsException
from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session)) -> User:
    """Register a new user."""
    try:
        statement = select(User).where(User.username == user_data.username)
        result = await session.execute(statement)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsException

        hashed_password = token_manager.get_password_hash(user_data.password)

        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
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
