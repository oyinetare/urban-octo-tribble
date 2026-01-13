from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8, max_length=100)


class UserResponse(UserBase):
    """Schema for user responses."""

    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
