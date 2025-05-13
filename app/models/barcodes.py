import uuid
import sqlalchemy as sa

import uuid as uuid_pkg

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


from sqlalchemy.dialects.postgresql import UUID


class Barcode(SQLModel, table=True):
    """
    Model to represent the Barcode table.

    id: Optional is declared only for Python's needs before a db object is
        created. This field cannot be null in the database.
    """

    __tablename__ = "barcodes"

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=sa.Column(
            UUID(as_uuid=True),
            primary_key=True,
            unique=True,
            index=True,
            server_default=sa.text("gen_random_uuid()")
        )
    )
    value: str = Field(
        sa_column=sa.Column(sa.VARCHAR(255), nullable=False, unique=True)
    )
    withdrawn: bool = Field(default=False, nullable=False)
    type_id: int = Field(foreign_key="barcode_types.id")
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    type: Optional["BarcodeType"] = Relationship(back_populates="barcodes")
