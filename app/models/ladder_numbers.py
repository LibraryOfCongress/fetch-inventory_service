import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class LadderNumber(SQLModel, table=True):
    """
    Model to represent the Ladder Numbers table.
    Ladder Numbers are unique within the table, but may be re-used 
    by Ladders which may be in different aisle sides from one another.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "ladder_numbers"

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, primary_key=True)
    )
    number: int = Field(sa_column=sa.Column(sa.SmallInteger, nullable=False, unique=True))
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

    # ladders assigned this number
    ladders: List['Ladder'] = Relationship(back_populates="ladder_number")
