from datetime import datetime

from sqlalchemy import BigInteger, func
from sqlmodel import Field, SQLModel

from app.utility import id_generator


class BaseModel(SQLModel):
    # Use BigInteger for large ID values from id_generator
    id: int = Field(
        default_factory=lambda: id_generator.generate(), primary_key=True, sa_type=BigInteger
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={
            "server_default": func.now(),
        },
    )

    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),  # Triggers update on every SAVE
        },
    )
