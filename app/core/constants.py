from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

    @property
    def scopes(self) -> list[str]:
        """Maps each role to its specific permissions."""
        base_scopes = ["read", "write"]
        mapping = {
            UserRole.ADMIN: base_scopes + ["admin"],
            UserRole.MODERATOR: base_scopes + ["moderate"],
            UserRole.USER: base_scopes,
        }
        return mapping[self]
