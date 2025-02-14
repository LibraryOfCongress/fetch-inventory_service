import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship



class BarcodeType(SQLModel, table=True):
    """
    Model to represent the Barcode Type table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "barcode_types"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    name: str = Field(sa_column=sa.Column(sa.VARCHAR(25), nullable=False, unique=True))
    allowed_pattern: str = Field(
        sa_column=sa.Column(
            sa.VARCHAR(25),
            nullable=False,
            unique=False,
            index=True,
            default="^.{25}$",
        )
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    barcodes: List["Barcode"] = Relationship(back_populates="type")
