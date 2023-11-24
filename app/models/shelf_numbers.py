import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class ShelfNumber(SQLModel, table=True):
    """
    Model to represent the Shelf Numbers table.
    Shelf Numbers are unique within the table, but may be re-used 
    by Shelves which may be along separate Ladders down an aisle's side.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "shelf_numbers"

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

    # shelves assigned this number
    shelves: List['Shelf'] = Relationship(back_populates="shelf_number")
