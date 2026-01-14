"""user_roles_updatedat_lastlogin

Revision ID: 76376918368f
Revises: dc9c7815e283
Create Date: 2026-01-14 10:56:55.990071

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "76376918368f"
down_revision: str | Sequence[str] | None = "dc9c7815e283"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. role is perfect with server_default='user'
    op.add_column("users", sa.Column("role", sa.String(), server_default="user", nullable=False))

    # 2. Add server_default=sa.func.now() so existing rows get a timestamp
    op.add_column(
        "users",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # 3. Setting nullable=True is better for last_login (or use a server_default)
    op.add_column("users", sa.Column("last_login", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_login")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "role")
