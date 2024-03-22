import uuid
import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ConveyanceBin(SQLModel, table=True):
    """
    Model to represent the Conveyance Bin table. AKA 'Over The Road' bin.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "conveyance_bins"

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.Integer, primary_key=True)
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id",
        nullable=False,
        unique=True,
        default=None
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    trays: List["Tray"] = Relationship(back_populates="conveyance_bin")
    barcode: Optional["Barcode"] = Relationship(sa_relationship_kwargs={"uselist": False})
