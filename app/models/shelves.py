import uuid

import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime
from pydantic import condecimal
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.owners import Owner
from app.models.ladders import Ladder
from app.models.container_types import ContainerType
from app.models.shelf_numbers import ShelfNumber


class Shelf(SQLModel, table=True):
    """
    Model to represent the shelves table.
    Shelves belong to Ladders. One ladder may have many shelves, which are
    ordered from bottom to top along the ladder.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint(
            "ladder_id", "shelf_number_id", name="uq_ladder_id_shelf_number_id"
        ),
        UniqueConstraint("barcode_id"),
    )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=False, default=None, unique=True
    )
    capacity: int = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=False, default=1)
    )
    available_space: int = Field(
        sa_column=sa.Column(sa.Integer, nullable=False, default=0)
    )
    height: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    width: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    depth: condecimal(decimal_places=2) = Field(
        sa_column=sa.Column(sa.Numeric(precision=4, scale=2), nullable=False)
    )
    sort_priority: Optional[int] = Field(
        sa_column=sa.SmallInteger, nullable=True, default=None
    )
    container_type_id: int = Field(foreign_key="container_types.id", nullable=False)
    shelf_number_id: int = Field(foreign_key="shelf_numbers.id", nullable=False)
    size_class_id: int = Field(foreign_key="size_class.id", nullable=False)
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    ladder_id: int = Field(foreign_key="ladders.id", nullable=False)
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    ladder: Ladder = Relationship(back_populates="shelves")
    owner: Owner = Relationship(back_populates="shelves")
    barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    shelf_number: ShelfNumber = Relationship(back_populates="shelves")
    container_type: ContainerType = Relationship(back_populates="shelves")
    shelf_positions: List["ShelfPosition"] = Relationship(back_populates="shelf")
    size_class: Optional["SizeClass"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
