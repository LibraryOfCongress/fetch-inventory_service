
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import Integer, String, Enum as SQLEnum, TIMESTAMP, ForeignKey, Index, BigInteger
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from app.database.base import Base
from app.models.users import User # Needed for injection

if TYPE_CHECKING:
    from app.models.shipping_jobs import ShippingJob
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
    from app.models.delivery_locations import DeliveryLocation

class ShippingBinStatus(str, Enum):
    Open = "Open"     # Active in a job, can add items
    Closed = "Closed" # Locked/Full/Done for the job

class ShippingBin(Base):
    """
    Model to represent the Shipping Bins table.
    """
    __tablename__ = "shipping_bins"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys
    shipping_job_id: Mapped[int] = mapped_column(ForeignKey("shipping_jobs.id"), nullable=False, index=True)
    
    # Barcode Identification
    barcode: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Location Assignment (Nullable until first item sets it)
    delivery_location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("delivery_locations.id"), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        SQLEnum(
            ShippingBinStatus,
            name="shipping_bin_status",
            nullable=False,
        ),
        default=ShippingBinStatus.Open,
    )

    # Clearing Logic
    cleared_dt: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    cleared_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    shipping_job: Mapped["ShippingJob"] = relationship(back_populates="bins")
    
    delivery_location: Mapped[Optional["DeliveryLocation"]] = relationship(lazy="selectin")
    
    items: Mapped[List["Item"]] = relationship("Item", backref=backref("shipping_bin", lazy="selectin"), foreign_keys="[Item.shipping_bin_id]", lazy="selectin")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship("NonTrayItem", backref=backref("shipping_bin", lazy="selectin"), foreign_keys="[NonTrayItem.shipping_bin_id]", lazy="selectin")
    
    cleared_by: Mapped[Optional["User"]] = relationship("User", backref=backref("cleared_shipping_bins", lazy="selectin"), foreign_keys=[cleared_by_id], lazy="selectin")

    # Composite Index for Auto-Clear Logic
    __table_args__ = (
        Index("idx_shipping_bin_barcode_uncleared", "barcode", "cleared_dt"),
    )


    @property
    def item_count(self) -> int:
        return len(self.items) if self.items is not None else 0

