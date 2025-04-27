import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import backref

from app.models.owner_tiers import OwnerTier
from app.models.items import Item


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

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    parent_owner_id: Optional[int] = Field(
        default=None, foreign_key="owners.id", nullable=True
    )
    name: str = Field(
        sa_column=sa.Column(
            sa.VARCHAR(150),
            nullable=False,
            index=True,
            default=None
        )
    )
    owner_tier_id: int = Field(
        foreign_key="owner_tiers.id",
        nullable=False,
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    owner_tier: OwnerTier = Relationship(back_populates="owners")
    shelves: List["Shelf"] = Relationship(back_populates="owner")
    accession_jobs: List["AccessionJob"] = Relationship(back_populates="owner")
    verification_jobs: List["VerificationJob"] = Relationship(back_populates="owner")
    children: List["Owner"] = Relationship(
        sa_relationship_kwargs=dict(
            cascade="all",
            backref=backref("parent_owner", remote_side="Owner.id"),
        )
    )
    items: List[Item] = Relationship(back_populates="owner")
    shelving_job_discrepancies: List["ShelvingJobDiscrepancy"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJobDiscrepancy.owner_id==Owner.id",
            "lazy": "selectin"
        }
    )
    items_retrieval_events: List["ItemRetrievalEvent"] = Relationship(
        back_populates="owner"
    )
    non_tray_items_retrieval_events: List["NonTrayItemRetrievalEvent"] = Relationship(
        back_populates="owner"
    )
    move_discrepancies: List["MoveDiscrepancy"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={
            "primaryjoin": "MoveDiscrepancy.owner_id==Owner.id",
            "lazy": "selectin"
        }
    )
