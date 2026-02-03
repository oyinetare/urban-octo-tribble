from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlmodel import Field, SQLModel

from app.utility import id_generator, utc_now


class BaseModel(SQLModel):
    # Use BigInteger for large ID values from id_generator
    id: int = Field(
        default_factory=lambda: id_generator.generate(), primary_key=True, sa_type=BigInteger
    )

    # Timestamps - PostgreSQL TIMESTAMP WITH TIME ZONE
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),  # Triggers update on every SAVE
        },
    )
