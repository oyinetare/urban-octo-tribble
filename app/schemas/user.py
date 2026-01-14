from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core import UserRole


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8, max_length=100)
    role: UserRole = Field(default=UserRole.USER)
    # tier: str | None = Field(default="free", max_length=50)


class UserResponse(UserBase):
    """Schema for user responses."""

    id: int
    is_active: bool
    role: UserRole
    # tier: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for JWT token response with OAuth2 scopes."""

    access_token: str
    token_type: str = "bearer"
    scopes: list[str] = Field(default=[], example=["read", "write", "admin"])
