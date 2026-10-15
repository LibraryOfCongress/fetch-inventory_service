# /app/models/non_tray_items.py - ULTIMATE, FINAL CORRECTED V2

import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, VARCHAR, TIMESTAMP, ForeignKey, Boolean, Integer, String, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Enum as SQLEnum

from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base

# --- CRITICAL: IMPORT TABLE OBJECTS FOR M2M ---
from app.models.link_tables import RefileNonTrayItemTable, NonTrayItemWithdrawalTable
# ----------------------------------------------

# --- ABSOLUTE FK IMPORTS (Must be available at runtime) ---
from app.models.owners import Owner
from app.models.size_class import SizeClass
from app.models.container_types import ContainerType
from app.models.media_types import MediaType
from app.models.accession_jobs import AccessionJob
from app.models.subcollection import Subcollection
from app.models.verification_jobs import VerificationJob
from app.models.shelving_jobs import ShelvingJob
from app.models.shelf_positions import ShelfPosition

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.barcodes import Barcode
    from app.models.refile_jobs import RefileJob
    from app.models.withdraw_jobs import WithdrawJob
    from app.models.requests import Request
    from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
    from app.models.move_discrepancies import MoveDiscrepancy
    from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
# -----------------------------------------------------


class NonTrayItemStatus(str, Enum):
    In = "In"
    Out = "Out"
    Requested = "Requested"
    PickList = "PickList"
    Withdrawn = "Withdrawn"
    Accessioned = "Accessioned"
    Verified = "Verified"
    Retrieved = "Retrieved"

class ILSSyncState(str, Enum):
    IN_SYNC = "IN_SYNC"
    PENDING_SYNC = "PENDING_SYNC"
    SYNC_ERROR = "SYNC_ERROR"


class NonTrayItem(Base): 
    """
    Model to represent the non_tray_items table.
    """
    __tablename__ = "non_tray_items"

    __table_args__ = (
        CheckConstraint(
            "(barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)",
            name="ck_non_tray_item_barcode_xor_withdrawn_barcode",
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Status (Enum)
    status: Mapped[Optional[str]] = mapped_column(
        SQLEnum(NonTrayItemStatus, name="non_tray_item_status", nullable=False),
        default=NonTrayItemStatus.In,
    )

    # ILS Sync State (Enum)
    ils_sync_state: Mapped[Optional[str]] = mapped_column(
        SQLEnum(ILSSyncState, name="ils_sync_state_enum", nullable=True, create_type=False),
        nullable=True,
    )

    # Barcode ID (UUID Foreign Key) - String literals are safe here
    barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("barcodes.id"), nullable=True, unique=True
    )

    # Withdrawn Barcode ID 
    withdrawn_barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("barcodes.id", name="withdrawn_non_tray_item_barcode_id"), unique=True, nullable=True
    )

    # Simple VARCHAR Fields
    withdrawn_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    withdrawn_internal_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    withdrawn_loc_bcodes: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Foreign Keys (Integer) - ABSOLUTE FK FIXES
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    size_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=True)
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True)
    subcollection_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Subcollection.__table__.c.id), nullable=True)
    accession_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(AccessionJob.__table__.c.id), nullable=True)
    verification_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(VerificationJob.__table__.c.id), nullable=True)
    shelving_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ShelvingJob.__table__.c.id), nullable=True)
    shelf_position_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ShelfPosition.__table__.c.id), nullable=True, unique=True)
    media_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(MediaType.__table__.c.id), nullable=True)
    shipping_bin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shipping_bins.id"), nullable=True)
    
    # Note: shelf_position_proposed_id does not reference another table
    shelf_position_proposed_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Boolean Fields
    scanned_for_accession: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_shelving: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_shipping: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_refile_queue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_refile: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Datetime Fields
    accession_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    withdrawal_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    shelved_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    scanned_for_refile_queue_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    scanned_for_refile_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    
    # Other Fields
    condition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    
    # --- PROPERTIES ---
    @property
    def last_requested_dt(self):
        if not self.requests: return None
        return max(request.create_dt for request in self.requests)

    @property
    def last_refiled_dt(self):
        if not self.refile_jobs: return None
        return max(refile_job.update_dt for refile_job in self.refile_jobs)

    @property
    def last_refile_job_id(self):
        if not self.refile_jobs: return None
        latest = max(self.refile_jobs, key=lambda j: j.update_dt)
        return latest.id

    @property
    def last_withdraw_job_id(self):
        if not self.withdraw_jobs: return None
        latest = max(self.withdraw_jobs, key=lambda j: j.update_dt)
        return latest.id

    @property
    def last_request_id(self):
        if not self.requests: return None
        latest = max(self.requests, key=lambda r: r.create_dt)
        return latest.id


    # --- RELATIONSHIPS ---
    
    # 1. Barcode (CRITICAL FIX: Use back_populates instead of backref)
    barcode: Mapped[Optional["Barcode"]] = relationship(
        back_populates="barcode_non_tray_item", foreign_keys=[barcode_id])
        
    # 2. Withdrawn Barcode (CRITICAL FIX: Use back_populates instead of backref)
    withdrawn_barcode: Mapped[Optional["Barcode"]] = relationship(
        back_populates="withdrawn_non_tray_item", foreign_keys=[withdrawn_barcode_id])

    # 3. Standard Relationships
    media_type: Mapped[Optional["MediaType"]] = relationship(back_populates="non_tray_items", foreign_keys=[media_type_id])
    size_class: Mapped[Optional["SizeClass"]] = relationship(back_populates="non_tray_items", foreign_keys=[size_class_id])
    container_type: Mapped[Optional["ContainerType"]] = relationship(back_populates="non_tray_items", foreign_keys=[container_type_id])
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="non_tray_items", foreign_keys=[owner_id])
    accession_job: Mapped[Optional["AccessionJob"]] = relationship(back_populates="non_tray_items", foreign_keys=[accession_job_id])
    verification_job: Mapped[Optional["VerificationJob"]] = relationship(back_populates="non_tray_items", foreign_keys=[verification_job_id])
    shelving_job: Mapped[Optional["ShelvingJob"]] = relationship(back_populates="non_tray_items", foreign_keys=[shelving_job_id])
    shelf_position: Mapped[Optional["ShelfPosition"]] = relationship(back_populates="non_tray_item", foreign_keys=[shelf_position_id])
    subcollection: Mapped[Optional["Subcollection"]] = relationship(back_populates="non_tray_items", foreign_keys=[subcollection_id])
    
    # 3. Reverse Relationships
    requests: Mapped[List["Request"]] = relationship(back_populates="non_tray_item")
    non_tray_items_retrieval_events: Mapped[List["NonTrayItemRetrievalEvent"]] = relationship(back_populates="non_tray_item")

    # 4. Many-to-Many Relationships (CRITICAL FIX: Use Manual Table Object)
    refile_jobs: Mapped[List["RefileJob"]] = relationship(
        back_populates="non_tray_items", 
        secondary=RefileNonTrayItemTable,
        primaryjoin=id == RefileNonTrayItemTable.c.non_tray_item_id,
        secondaryjoin="RefileJob.id == refile_non_tray_items.c.refile_job_id"
    )

    withdraw_jobs: Mapped[List["WithdrawJob"]] = relationship(
        back_populates="non_tray_items", 
        secondary=NonTrayItemWithdrawalTable,
        primaryjoin=id == NonTrayItemWithdrawalTable.c.non_tray_item_id,
        secondaryjoin="WithdrawJob.id == non_tray_item_withdrawals.c.withdraw_job_id"
    )

    # 5. Discrepancy Relationships
    shelving_job_discrepancies: Mapped[List["ShelvingJobDiscrepancy"]] = relationship(
        back_populates="non_tray_item",
        primaryjoin="ShelvingJobDiscrepancy.non_tray_item_id==NonTrayItem.id",
        lazy="selectin"
    )
    
    move_discrepancies: Mapped[List["MoveDiscrepancy"]] = relationship(
        back_populates="non_tray_item",
        primaryjoin="MoveDiscrepancy.non_tray_item_id==NonTrayItem.id",
        lazy="selectin"
    )