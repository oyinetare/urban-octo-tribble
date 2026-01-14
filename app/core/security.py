from pwdlib import PasswordHash


class TokenManager:
    """Centralized manager for password hashing and JWT token operations."""

    def __init__(self):
        self.password_hash = PasswordHash.recommended()

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.password_hash.hash(password)


# Global instance
token_manager = TokenManager()
