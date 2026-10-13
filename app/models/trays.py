# /app/models/trays.py - ULTIMATE, FINAL CORRECTED V2

import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, VARCHAR, TIMESTAMP, ForeignKey, Boolean, Integer, String, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from pydantic import condecimal 

# NEW IMPORTS: Base and all necessary model dependencies
from app.database.base import Base
# --- CRITICAL: DIRECT IMPORTS FOR ABSOLUTE FK LOOKUP (MUST BE OUTSIDE TYPE_CHECKING) ---
from app.models.accession_jobs import AccessionJob
from app.models.verification_jobs import VerificationJob
from app.models.shelving_jobs import ShelvingJob
from app.models.container_types import ContainerType
from app.models.size_class import SizeClass
from app.models.owners import Owner
from app.models.media_types import MediaType
from app.models.shelf_positions import ShelfPosition
from app.models.conveyance_bins import ConveyanceBin
from app.models.tray_withdrawal import TrayWithdrawal 
from app.models.withdraw_jobs import WithdrawJob 
# ----------------------------------------------------------------------------------------

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.barcodes import Barcode
    from app.models.items import Item
    from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
    from app.models.move_discrepancies import MoveDiscrepancy
    
# -----------------------------------------------------


class Tray(Base): 
    """
    Model to represent the trays table.
    """
    __tablename__ = "trays"

    __table_args__ = (
        CheckConstraint(
            "(barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)",
            name="ck_tray_barcode_xor_withdrawn_barcode",
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Key Fields (Integer) - CRITICAL: ABSOLUTE FK FIX
    accession_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(AccessionJob.__table__.c.id), nullable=True)
    verification_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(VerificationJob.__table__.c.id), nullable=True)
    shelving_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ShelvingJob.__table__.c.id), nullable=True)
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True)
    size_class_id: Mapped[int] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    media_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(MediaType.__table__.c.id), nullable=True)
    shelf_position_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ShelfPosition.__table__.c.id), nullable=True, unique=True)
    conveyance_bin_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ConveyanceBin.__table__.c.id), nullable=True)

    # Note: shelf_position_proposed_id does not reference another table
    shelf_position_proposed_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Barcode ID (UUID Foreign Key)
    barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("barcodes.id"), nullable=True, unique=True
    )

    # Withdrawn Barcode ID (Custom UUID Foreign Key)
    withdrawn_barcode_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("barcodes.id", name="withdrawn_tray_barcode_id"), unique=True, nullable=True
    )

    # Simple VARCHAR Fields
    withdrawn_location: Mapped[Optional[str]] = mapped_column(String(175), nullable=True)
    withdrawn_internal_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    withdrawn_loc_bcodes: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Boolean Fields
    scanned_for_accession: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scanned_for_shelving: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collection_accessioned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collection_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Datetime Fields
    accession_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    shelved_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    withdrawal_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    
    # --- RELATIONSHIPS ---

    # 1. Barcode (CRITICAL FIX: Use back_populates instead of backref)
    barcode: Mapped[Optional["Barcode"]] = relationship(
        back_populates="barcode_tray", foreign_keys=[barcode_id])
    
    # 2. Withdrawn Barcode (CRITICAL FIX: Use back_populates instead of backref)
    withdrawn_barcode: Mapped[Optional["Barcode"]] = relationship(
        back_populates="withdrawn_tray", foreign_keys=[withdrawn_barcode_id])

    # 3. Standard One-to-One Relationships
    media_type: Mapped[Optional["MediaType"]] = relationship(back_populates="trays")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="trays")
    container_type: Mapped[Optional["ContainerType"]] = relationship(back_populates="trays")
    size_class: Mapped[Optional["SizeClass"]] = relationship(back_populates="trays")
    shelf_position: Mapped[Optional["ShelfPosition"]] = relationship(back_populates="tray")
    conveyance_bin: Mapped[Optional["ConveyanceBin"]] = relationship(back_populates="trays")
    
    # 4. Standard One-to-Many Relationships
    accession_job: Mapped[Optional["AccessionJob"]] = relationship(back_populates="trays")
    verification_job: Mapped[Optional["VerificationJob"]] = relationship(back_populates="trays")
    shelving_job: Mapped[Optional["ShelvingJob"]] = relationship(back_populates="trays")
    items: Mapped[List["Item"]] = relationship(back_populates="tray")

    # 5. Many-to-Many Relationships (CRITICAL FIX: lambda for circular M2M)
    withdraw_jobs: Mapped[List["WithdrawJob"]] = relationship(
        back_populates="trays", 
        secondary=lambda: TrayWithdrawal.__table__
    )

    # 6. Custom Primaryjoin Relationships
    shelving_job_discrepancies: Mapped[List["ShelvingJobDiscrepancy"]] = relationship(
        back_populates="tray",
        primaryjoin="ShelvingJobDiscrepancy.tray_id==Tray.id",
        lazy="selectin"
    )
    move_discrepancies: Mapped[List["MoveDiscrepancy"]] = relationship(
        back_populates="tray",
        primaryjoin="MoveDiscrepancy.tray_id==Tray.id",
        lazy="selectin"
    )