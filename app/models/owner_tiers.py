import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class OwnerTier(SQLModel, table=True):
    """
    Model to represent Owner Tiers table

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "owner_tiers"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    level: int = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=False, unique=True, default=None)
    )
    name: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=False, unique=True, default=None)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # owners assigned this tier
    owners: List["Owner"] = Relationship(back_populates="owner_tier")
