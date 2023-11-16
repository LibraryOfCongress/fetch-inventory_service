import uuid
import sqlalchemy as sa

import uuid as uuid_pkg

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

from sqlalchemy.dialects.postgresql import UUID


class Barcode(SQLModel, table=True):
    """
    Model to represent the Barcode table.

    id: Optional is declared only for Python's needs before a db object is
        created. This field cannot be null in the database.
    """

    __tablename__ = "barcodes"

    id: Optional[uuid.UUID] = Field(sa_column=sa.Column(
        UUID(as_uuid=True),
        primary_key=True,
        unique=True,
        default=uuid.uuid4,
        index=True
    ))
    value: str = Field(
        max_length=255, sa_column=sa.VARCHAR, nullable=False, unique=True
    )
    type_id: int = Field(foreign_key="barcode_types.id")
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

