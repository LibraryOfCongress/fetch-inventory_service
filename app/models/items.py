
# /app/models/items.py - ULTIMATE, FINAL CORRECTED V2 (ABSOLUTE FK)

import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref 
from sqlalchemy import BigInteger, VARCHAR, TIMESTAMP, ForeignKey, Boolean, Integer, String, CheckConstraint, text
from sqlalchemy.types import Enum as SQLEnum  
from sqlalchemy.dialects.postgresql import UUID

from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base

# --- CRITICAL: DIRECT IMPORTS FOR ABSOLUTE FK LOOKUP ---
from app.models.size_class import SizeClass
from app.models.container_types import ContainerType
from app.models.owners import Owner
from app.models.subcollection import Subcollection
from app.models.accession_jobs import AccessionJob 
from app.models.verification_jobs import VerificationJob
from app.models.media_types import MediaType
from app.models.trays import Tray
from app.models.link_tables import RefileItemTable, ItemWithdrawalTable
# -----------------------------------------------------

# --- CRITICAL: DEFERRED IMPORTS (for circularity and clean code) ---
if TYPE_CHECKING:
    from app.models.items import Item
    from app.models.accession_jobs import AccessionJob
    from app.models.verification_jobs import VerificationJob
    from app.models.shelving_jobs import ShelvingJob
    from app.models.container_types import ContainerType
    from app.models.size_class import SizeClass
    from app.models.owners import Owner
    from app.models.media_types import MediaType
    from app.models.shelf_positions import ShelfPosition
    from app.models.conveyance_bins import ConveyanceBin
    from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
    from app.models.move_discrepancies import MoveDiscrepancy
    from app.models.tray_withdrawal import TrayWithdrawal
    from app.models.withdraw_jobs import WithdrawJob
    from app.models.barcodes import Barcode
    from app.models.shipping_bins import ShippingBin
# -------------------------------------------------------------------


class ItemStatus(str, Enum):
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


class Item(Base): 
    """
    Model to represent the Items table.
    """

    __table_args__ = (
        CheckConstraint(
            "(barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)",
            name="ck_items_barcode_xor_withdrawn_barcode",
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)
    
    # Status (Enum)
    status: Mapped[Optional[str]] = mapped_column(
        SQLEnum(ItemStatus, name="item_status", nullable=False, create_type=False),
        default=ItemStatus.In,
    )
    
    # ILS Sync State (Enum)
    ils_sync_state: Mapped[Optional[str]] = mapped_column(
        SQLEnum(ILSSyncState, name="ils_sync_state_enum", nullable=True, create_type=False),
        nullable=True,
    )
    
    # Barcode ID (UUID Foreign Key)
    barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("barcodes.id"), nullable=True, unique=True)
    
    # Withdrawn Barcode ID (Custom UUID Foreign Key)
    withdrawn_barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("barcodes.id", name="withdrawn_item_barcode_id"), unique=True, nullable=True)
    
    # Simple VARCHAR Fields
    withdrawn_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    withdrawn_internal_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    withdrawn_loc_bcodes: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    
    # Foreign Keys (Integer)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    size_class_id: Mapped[int] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=True)
    tray_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Tray.__table__.c.id), nullable=True)
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True)
    subcollection_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Subcollection.__table__.c.id), nullable=True)
    accession_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(AccessionJob.__table__.c.id), nullable=True)
    verification_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(VerificationJob.__table__.c.id), nullable=True)
    media_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(MediaType.__table__.c.id), nullable=True)
    shipping_bin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("shipping_bins.id"), nullable=True)
    
    # Boolean Fields
    scanned_for_accession: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_shipping: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_refile_queue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_refile: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Longer Text/Data Fields
    title: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    arbitrary_data: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Datetime Fields
    accession_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    withdrawal_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    scanned_for_refile_queue_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    scanned_for_refile_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

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


    # --- RELATIONSHIPS (FINAL FIX: Explicit foreign_keys matching the Mapped column) ---

    # 1. Barcode (Custom backref, foreign_keys)
    barcode: Mapped[Optional["Barcode"]] = relationship(
        back_populates="barcode_item", foreign_keys=[barcode_id])
    
    # 2. Withdrawn Barcode (Custom backref, foreign_keys)
    withdrawn_barcode: Mapped[Optional["Barcode"]] = relationship(
        back_populates="withdrawn_item", foreign_keys=[withdrawn_barcode_id])
    
    # 3. Standard One-to-One Relationships (All now have explicit foreign_keys)
    accession_job: Mapped[Optional["AccessionJob"]] = relationship(back_populates="items", foreign_keys=[accession_job_id])
    verification_job: Mapped[Optional["VerificationJob"]] = relationship(back_populates="items", foreign_keys=[verification_job_id])
    subcollection: Mapped[Optional["Subcollection"]] = relationship(back_populates="items", foreign_keys=[subcollection_id])
    tray: Mapped[Optional["Tray"]] = relationship(back_populates="items", foreign_keys=[tray_id])
    media_type: Mapped[Optional["MediaType"]] = relationship(back_populates="items", foreign_keys=[media_type_id])
    size_class: Mapped[Optional["SizeClass"]] = relationship(back_populates="items", foreign_keys=[size_class_id])
    container_type: Mapped[Optional["ContainerType"]] = relationship(uselist=False, foreign_keys=[container_type_id])
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="items", foreign_keys=[owner_id])
    
    # 4. Other Relationships
    requests: Mapped[List["Request"]] = relationship(back_populates="item")
    items_retrieval_events: Mapped[List["ItemRetrievalEvent"]] = relationship(back_populates="item")
    
    # 5. Move Discrepancies (Custom primaryjoin)
    move_discrepancies: Mapped[List["MoveDiscrepancy"]] = relationship(
        back_populates="item", primaryjoin="MoveDiscrepancy.item_id==Item.id", lazy="selectin")
    
    # 6. Many-to-Many Relationships (CRITICAL FIX: lambda for deferred M2M)
    refile_jobs: Mapped[List["RefileJob"]] = relationship(
        back_populates="items", 
        secondary=RefileItemTable, # Direct Table Object
        primaryjoin="Item.id == refile_items.c.item_id",
        secondaryjoin="RefileJob.id == refile_items.c.refile_job_id"
    )
    withdraw_jobs: Mapped[List["WithdrawJob"]] = relationship(
        back_populates="items", 
        secondary=ItemWithdrawalTable, # Direct Table Object
        primaryjoin="Item.id == item_withdrawals.c.item_id",
        secondaryjoin="WithdrawJob.id == item_withdrawals.c.withdraw_job_id"
    )

    # 7. Shipping Relationship - defined via backref on ShippingBin.items
    # Attribute created dynamically: shipping_bin