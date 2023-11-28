import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint

from app.models.owner_tiers import OwnerTier


class Owner(SQLModel, table=True):
    """
    Model to represent Owners table

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """
    __tablename__ = "owners"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "owner_tier_id",
            name="uq_name_owner_tier_id"
        ),
    )

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, primary_key=True)
    )
    name: str = Field(
        max_length=150,
        sa_column=sa.VARCHAR,
        nullable=False,
        default=None
    )
    owner_tier_id: int = Field(
        foreign_key="owner_tiers.id",
        nullable=False,
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

    owner_tier: OwnerTier = Relationship(back_populates="owners")
    shelves: List['Shelf'] = Relationship(back_populates="owner")
