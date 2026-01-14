from typing import Any

from fastapi import status


class AppException(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers


class UserAlreadyExistsException(AppException):
    """Exception for user already exists."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User with this email or username already exists",
        )
