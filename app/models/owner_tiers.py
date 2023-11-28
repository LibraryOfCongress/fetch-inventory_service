import sqlalchemy as sa

from pydantic import conint
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint


class OwnerTier(SQLModel, table=True):
    """
    Model to represent Owner Tiers table

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "owner_tiers"

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, primary_key=True)
    )
    level: int = Field(
        sa_column=sa.SmallInteger,
        nullable=False,
        unique=True,
        default=None
    )
    name: str = Field(
        max_length=50,
        sa_column=sa.VARCHAR,
        nullable=False,
        unique=True,
        default=None
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

    # owners assigned this tier
    owners: List['Owner'] = Relationship(back_populates="owner_tier")
