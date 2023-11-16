import uuid
import sqlalchemy as sa

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.ladder_numbers import LadderNumber
from app.models.sides import Side


class Ladder(SQLModel, table=True):
    """
    Model to represent Ladders table

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "ladders"
    __table_args__ = (
        UniqueConstraint("side_id", "ladder_number_id", name="uq_side_id_ladder_number_id"),
    )

    id: Optional[int] = Field(
        primary_key=True,
        sa_column=sa.Integer, 
        default=None
    )
    ladder_number_id: int = Field(
        foreign_key="ladder_numbers.id",
        nullable=False,
    )
    side_id: int = Field(foreign_key="sides.id", nullable=False)
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

    side: Side = Relationship(back_populates="ladders")
    ladder_number: LadderNumber = Relationship(back_populates="ladders")
