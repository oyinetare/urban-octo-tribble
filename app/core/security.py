from datetime import datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()


class TokenManager:
    """Centralized manager for password hashing and JWT token operations."""

    def __init__(self):
        self.password_hash = PasswordHash.recommended()

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.password_hash.hash(password)

    def verify_password_hash(self, password, hashed_password) -> bool:
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
        """Create a JWT access token with embedded rate limits."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Standard practice: Use UTC for JWT 'exp'
        expire = datetime.now() + expires_delta

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
        """Decode and verify a JWT token."""
        try:
            # leeway handles clock skew between different servers
            return jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], leeway=10
            )
        except (InvalidTokenError, Exception):
            return None

    def create_refresh_token(
        self,
        data: dict,
        expires_delta: timedelta = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ) -> str:
        """Create a JWT refresh token (longer-lived)."""
        to_encode = data.copy()

        expire = datetime.now() + expires_delta

        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def get_token_expiry(self, token: str) -> datetime | None:
        """Extract expiration time from token."""
        try:
            payload = self.decode_token(token)
            if payload is not None:
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    return datetime.fromtimestamp(exp_timestamp)
        except Exception:
            pass
        return None


# Global instance
token_manager = TokenManager()
