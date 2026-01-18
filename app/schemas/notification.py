from pydantic import BaseModel


class NotificationCreate(BaseModel):
    """Schema for creating notification."""

    user_id: int
    type: str
    title: str
    message: str
    action_url: str | None = None


class NotificationResponse(BaseModel):
    """Schema for notification response."""

    id: int
    user_id: int
    type: str
    title: str
    message: str
    action_url: str | None
    is_read: bool
    created_at: str
