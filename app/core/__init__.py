# app/core/__init__.py
"""
Core module imports.

Import order matters to avoid circular dependencies.
"""

# 1. Config (no dependencies)
from app.config import get_settings

# 2. Constants (no dependencies)
from app.core.constants import UserRole, UserTier

# 4. Database (needs id_generator)
from app.core.database import AsyncSessionLocal, get_session, init_db

# 5. Redis (no model dependencies)
from app.core.redis import redis_service
from app.core.security import token_manager

# 3. Utilities (minimal dependencies)
from app.core.snowflake import id_generator

# DON'T import notification_service here - it creates circular import
# Import it directly where needed instead

__all__ = [
    "get_settings",
    "UserRole",
    "UserTier",
    "id_generator",
    "token_manager",
    "AsyncSessionLocal",
    "get_session",
    "init_db",
    "redis_service",
]
