import sqlalchemy as sa

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.shelves import Shelf
from app.models.shelf_position_numbers import ShelfPositionNumber


class ShelfPosition(SQLModel, table=True):
    """
    Model to represent the shelf positions table.
    One shelf may have many shelf positions.
    Shelf positions numbering is unique within a given shelf.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "shelf_positions"
    __table_args__ = (
        UniqueConstraint("shelf_id", "shelf_position_number_id", name="uq_shelf_id_shelf_position_number_id"),
    )

    id: Optional[int] = Field(sa_column=sa.Column(
        sa.BigInteger,
        primary_key=True
    ))

    shelf_position_number_id: int = Field(
        foreign_key="shelf_position_numbers.id",
        nullable=False
    )
    shelf_id: int = Field(
        foreign_key="shelves.id",
        nullable=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime,
        default=datetime.utcnow(),
        nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime,
        default=datetime.utcnow(),
        nullable=False
    )

    shelf_position_number: ShelfPositionNumber = Relationship(back_populates="shelf_positions")

    shelf: Shelf = Relationship(back_populates="shelf_positions")
