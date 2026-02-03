from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.utility import utc_now

settings = get_settings()


class TokenManager:
    """Centralized manager for password hashing and JWT token operations."""

    def __init__(self):
        self.password_hash = PasswordHash.recommended()

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.password_hash.hash(password)

    def verify_password_hash(self, password: str, hashed_password: str) -> bool:
        """Verify password hash."""
        return self.password_hash.verify(password, hashed_password)

    def create_access_token(
        self,
        user_id: int,
        username: str,
        tier_limit: int,
        scopes: list[str] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a JWT access token with embedded rate limits.

        Args:
            user_id: User ID
            username: Username
            tier_limit: Rate limit tier
            scopes: User scopes/permissions
            expires_delta: Token expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)

        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Use UTC for JWT 'exp' - this is critical for token validation
        expire = utc_now() + expires_delta

        to_encode = {
            "sub": username,
            "id": user_id,
            "tier_limit": tier_limit,  # Embedded for middleware performance
            "scopes": scopes or [],
            "exp": expire,
            "type": "access",
        }

        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_token(self, token: str) -> dict | None:
        """
        Decode and verify a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            # leeway handles clock skew between different servers
            return jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], leeway=10
            )
        except (InvalidTokenError, Exception):
            return None

    def create_refresh_token(
        self,
        user_id: int,
        username: str,
        scopes: list[str] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a JWT refresh token (longer-lived).

        Args:
            user_id: User ID
            username: Username
            scopes: User scopes/permissions
            expires_delta: Token expiration time (defaults to REFRESH_TOKEN_EXPIRE_DAYS)

        Returns:
            Encoded JWT refresh token
        """
        if expires_delta is None:
            # Convert days to timedelta - this was the bug!
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Use UTC for JWT 'exp'
        expire = datetime.now(UTC) + expires_delta

        to_encode = {
            "sub": username,
            "id": user_id,
            "scopes": scopes or [],
            "exp": expire,
            "type": "refresh",
        }

        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_refresh_token(self, token: str) -> dict | None:
        """
        Verify a refresh token and return its payload.

        Args:
            token: JWT refresh token

        Returns:
            Decoded payload if valid refresh token, None otherwise
        """
        payload = self.decode_token(token)

        if payload is None:
            return None

        # Verify it's actually a refresh token
        if payload.get("type") != "refresh":
            return None

        return payload

    def get_token_expiry(self, token: str) -> datetime | None:
        """
        Extract expiration time from token.

        Args:
            token: JWT token

        Returns:
            Expiration datetime or None if invalid
        """
        try:
            payload = self.decode_token(token)
            if payload is not None:
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    # Return timezone-aware datetime
                    return datetime.fromtimestamp(exp_timestamp, tz=UTC)
        except Exception:
            pass
        return None

    def get_token_type(self, token: str) -> str | None:
        """
        Get the type of token (access or refresh).

        Args:
            token: JWT token

        Returns:
            Token type ('access' or 'refresh') or None if invalid
        """
        payload = self.decode_token(token)
        if payload:
            return payload.get("type")
        return None


# Global instance
token_manager = TokenManager()
