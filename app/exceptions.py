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


class UserNotFoundException(AppException):
    """Exception for user not found."""

    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message="User not found")


class CredentialsException(AppException):
    """Exception for invalid credentials."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InactiveUserException(AppException):
    """Exception for inactive user account"""

    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message="Inactive user")


class DocumentNotFoundException(AppException):
    """Exception for document not found"""

    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message="Document not found")


class NotAuthorizedDocumenAccessException(AppException):
    """Exception for not authorized to access document"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, message="Not authorized to access this document"
        )


class RequiresRoleException(AppException):
    """Exception for requires role"""

    def __init__(self, required_role: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, message=f"Requires {required_role} role"
        )


class InsufficientScopesException(AppException):
    """Exception for insufficient OAuth2 scopes"""

    def __init__(self, required_scopes: list[str], provided_scopes: list[str]):
        details = {
            "required_scopes": required_scopes,
            "provided_scopes": provided_scopes,
        }
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Insufficient permissions. Required scopes not present in token.",
            details=details,
            headers={"WWW-Authenticate": f'Bearer scope="{" ".join(required_scopes)}"'},
        )


class StorageException(AppException):
    """Exception for when a storage operation fails."""

    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=message)


class InvalidFileException(AppException):
    """Exception for when an uploaded file is invalid."""

    def __init__(self, message: str = "Invalid file"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, message=message)
