import uuid
import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class Building(SQLModel, table=True):
    """
    Model to represent the buildings table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "buildings"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.SmallInteger, default=None)
    name: Optional[str] = Field(
        max_length=25,
        sa_column=sa.VARCHAR,
        nullable=True,
        default=None
    )
    barcode: Optional[uuid.UUID] = Field(sa_column=sa.UUID, nullable=True, default=None)
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

    # modules in a building
    modules: List['Module'] = Relationship(back_populates="building")
    # aisles in a building
    aisles: List['Aisle'] = Relationship(back_populates="building")