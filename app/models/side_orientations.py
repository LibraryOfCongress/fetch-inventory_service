import sqlalchemy as sa
from sqlalchemy import Column, DateTime

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint


class SideOrientation(SQLModel, table=True):
    """
    Model to represent the side orientations (Left, Right).
        SideOrientation is a Side configuration in an Aisle.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "side_orientations"
    __table_args__ = (UniqueConstraint("name", name="uq_side_orientation_name"),)

    id: Optional[int] = Field(primary_key=True, sa_column=sa.SmallInteger, default=None)
    name: str = Field(max_length=5, sa_column=sa.VARCHAR, nullable=False, index=True)
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    # Sides in xyz orientation
    sides: List["Side"] = Relationship(back_populates="side_orientation")
