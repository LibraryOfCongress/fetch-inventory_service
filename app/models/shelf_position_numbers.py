import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ShelfPositionNumber(SQLModel, table=True):
    """
    Model to represent the Shelf Position Numbers table.
    Shelf Position Numbers are unique within the table, but may be re-used 
    by Shelf Positions which may be across separate Shelves.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "shelf_position_numbers"

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, primary_key=True)
    )
    number: int = Field(sa_column=sa.Column(
        sa.SmallInteger,
        nullable=False,
        unique=True
    ))
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

    # shelf positions assigned this number
    shelf_positions: List['ShelfPosition'] = Relationship(back_populates="shelf_position_number")
