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


class UserTier(StrEnum):
    FREE = "free"
    PAID = "paid"
    ENTERPRISE = "enterprise"

    # allowed requests per minute for rate limiting
    @property
    def limit(self) -> int:
        mapping = {
            UserTier.FREE: 10,
            UserTier.PAID: 100,
            UserTier.ENTERPRISE: 1000,
        }

        return mapping[self]


class SortOrder(StrEnum):
    """Sort order enumeration"""

    ASC = "asc"
    DESC = "desc"
