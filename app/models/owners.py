# /code/app/models/owners.py - FINAL CORRECTED V2

import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import SmallInteger, Integer, String, VARCHAR, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base
from app.models.owner_tiers import OwnerTier

if TYPE_CHECKING:
    from app.models.items import Item
    from app.models.shelves import Shelf 
    from app.models.accession_jobs import AccessionJob
    from app.models.verification_jobs import VerificationJob
    from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
    from app.models.item_retrieval_events import ItemRetrievalEvent
    from app.models.non_tray_items import NonTrayItem # <--- NEEDED
    from app.models.trays import Tray # <--- NEEDED
    from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
    from app.models.move_discrepancies import MoveDiscrepancy
    from app.models.owner_delivery_locations import OwnerDeliveryLocation
    from app.models.ils_configurations import ILSConfiguration
# -----------------------------------------------------


class Owner(Base): 
    """
    Model to represent Owners table
    """
    __tablename__ = "owners"

    __table_args__ = (
        UniqueConstraint("name", "owner_tier_id", name="uq_name_owner_tier_id"),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Self-Referential Foreign Key
    parent_owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("owners.id"), nullable=True)

    # Foreign Key to ILSConfiguration (Hierarchical Inheritance)
    ils_configuration_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("ils_configurations.id"), nullable=True)

    # Name field
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True, default=None)

    # Foreign Key to OwnerTier
    owner_tier_id: Mapped[int] = mapped_column(ForeignKey(OwnerTier.__table__.c.id), nullable=False)
    
    # --- RELATIONSHIPS ---

    # 1. Owner Tier
    owner_tier: Mapped[OwnerTier] = relationship(back_populates="owners")
    
    # 2. Children (Self-Referential)
    children: Mapped[List["Owner"]] = relationship(
        cascade="all, delete-orphan", 
        backref=backref("parent_owner", remote_side=[id]), 
    )
    
    # 3. Standard One-to-Many Relationships
    shelves: Mapped[List["Shelf"]] = relationship(back_populates="owner")
    accession_jobs: Mapped[List["AccessionJob"]] = relationship(back_populates="owner")
    verification_jobs: Mapped[List["VerificationJob"]] = relationship(back_populates="owner")
    items: Mapped[List["Item"]] = relationship(back_populates="owner")
    
    # CRITICAL FIX: Add missing inverse relationships
    trays: Mapped[List["Tray"]] = relationship(back_populates="owner")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="owner")

    # 4. Other Relations
    items_retrieval_events: Mapped[List["ItemRetrievalEvent"]] = relationship(back_populates="owner")
    non_tray_items_retrieval_events: Mapped[List["NonTrayItemRetrievalEvent"]] = relationship(back_populates="owner")

    # 5. Custom Primaryjoin Relationships
    shelving_job_discrepancies: Mapped[List["ShelvingJobDiscrepancy"]] = relationship(
        back_populates="owner",
        primaryjoin="ShelvingJobDiscrepancy.owner_id==Owner.id",
        lazy="selectin"
    )
    move_discrepancies: Mapped[List["MoveDiscrepancy"]] = relationship(
        back_populates="owner",
        primaryjoin="MoveDiscrepancy.owner_id==Owner.id",
        lazy="selectin"
    )

    # 6. Owner-DeliveryLocation Relationship
    owner_delivery_locations: Mapped[List["OwnerDeliveryLocation"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    # 7. ILS Configuration Relationship
    ils_configuration: Mapped[Optional["ILSConfiguration"]] = relationship(back_populates="owners")

    @property
    def resolved_ils_configuration_id(self):
        """
        Recursively resolves the ILS Configuration ID by checking this owner,
        then iterating up the parent hierarchy until one is found or it hits None.
        """
        if self.ils_configuration_id is not None:
            return self.ils_configuration_id
        if self.parent_owner:
            return self.parent_owner.resolved_ils_configuration_id
        return None