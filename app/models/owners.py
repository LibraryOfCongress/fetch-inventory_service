import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import backref

from app.models.owner_tiers import OwnerTier


class Owner(SQLModel, table=True):
    """
    Model to represent Owners table

          id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "owners"
    __table_args__ = (
        UniqueConstraint("name", "owner_tier_id", name="uq_name_owner_tier_id"),
    )

    id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, primary_key=True)
    )
    parent_owner_id: Optional[int] = Field(
        default=None,
        foreign_key="owners.id",
        nullable=True
    )
    name: str = Field(
        max_length=150, sa_column=sa.VARCHAR, nullable=False, default=None
    )
    owner_tier_id: int = Field(
        foreign_key="owner_tiers.id",
        nullable=False,
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    owner_tier: OwnerTier = Relationship(back_populates="owners")
    shelves: List['Shelf'] = Relationship(back_populates="owner")
    accession_jobs: List['AccessionJob'] = Relationship(back_populates="owner")
    verification_jobs: List["VerificationJob"] = Relationship(back_populates="owner")
    children: List["Owner"] = Relationship(
        sa_relationship_kwargs=dict(
        cascade="all",
        backref=backref("parent_owner", remote_side="Owner.id"),
        )
    )
