from datetime import datetime

from fastapi import APIRouter, status

from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate) -> User:
    """Register a new user."""
    user = User(
        id="1",
        email=user_data.email,
        username=user_data.username,
        hashed_password=user_data.password,
        is_active=True,
        created_at=datetime.now(),
    )

    return user
