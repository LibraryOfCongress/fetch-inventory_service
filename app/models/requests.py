# /code/app/models/requests.py - ULTIMATE, FINAL CORRECTED V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import BigInteger, Integer, Enum as SQLEnum, VARCHAR, ForeignKey, Boolean, String, CheckConstraint, select, func

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum

from app.database.base import Base

# --- CRITICAL: DIRECT IMPORTS FOR ABSOLUTE FK LOOKUP ---
# These models must be imported at runtime to use Model.__table__.c.id
# This is safe provided these models do not import 'Request' at runtime (they should use TYPE_CHECKING)
from app.models.pick_lists import PickList
from app.models.request_types import RequestType
from app.models.delivery_locations import DeliveryLocation
from app.models.priorities import Priority
from app.models.buildings import Building
from app.models.batch_upload import BatchUpload
from app.models.users import User
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem

# -----------------------------------------------------

class RequestStatus(str, Enum):
    New = "New"
    PickList = "PickList"
    Retrieved = "Retrieved"
    Completed = "Completed"


class Request(Base):
    """
    Model represents the requests table.
    """
    __tablename__ = "requests"

    __table_args__ = (
        CheckConstraint(
            "(item_id IS NULL AND non_tray_item_id IS NOT NULL) OR (non_tray_item_id IS NULL AND item_id IS NOT NULL)",
            name="ck_item_xor_non_tray",
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Status (Enum)
    status: Mapped[Optional[str]] = mapped_column(
        SQLEnum(
            RequestStatus,
            name="request_status",
            nullable=False,
        ),
        default=RequestStatus.New,
    )

    # --- Foreign Keys (Absolute References) ---
    
    # Metadata FKs
    request_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(RequestType.__table__.c.id), nullable=True)
    building_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Building.__table__.c.id), nullable=True)
    delivery_location_id: Mapped[Optional[int]] = mapped_column(ForeignKey(DeliveryLocation.__table__.c.id), nullable=True)
    priority_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Priority.__table__.c.id), nullable=True)
    
    # Core Association FKs
    pick_list_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PickList.__table__.c.id), nullable=True)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Item.__table__.c.id), nullable=True)
    non_tray_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey(NonTrayItem.__table__.c.id), nullable=True)
    batch_upload_id: Mapped[Optional[int]] = mapped_column(ForeignKey(BatchUpload.__table__.c.id), nullable=True, index=True)
    requested_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(User.__table__.c.id), nullable=True)
    
    # Fields
    external_request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    requestor_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    fulfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # --- RAM EFFICIENT METADATA (SQL SIDE) ---
    @hybrid_property
    def item_barcode(self) -> Optional[str]:
        if self.item and self.item.barcode:
            return self.item.barcode.value
        if self.non_tray_item and self.non_tray_item.barcode:
            return self.non_tray_item.barcode.value
        return None

    @item_barcode.expression
    @classmethod
    def item_barcode(cls):
        from app.models.items import Item
        from app.models.non_tray_items import NonTrayItem
        from app.models.barcodes import Barcode
        item_barcode_subq = (
            select(Barcode.value)
            .join(Item, Item.barcode_id == Barcode.id)
            .where(Item.id == cls.item_id)
            .scalar_subquery()
        )
        non_tray_barcode_subq = (
            select(Barcode.value)
            .join(NonTrayItem, NonTrayItem.barcode_id == Barcode.id)
            .where(NonTrayItem.id == cls.non_tray_item_id)
            .scalar_subquery()
        )
        return func.coalesce(item_barcode_subq, non_tray_barcode_subq).label("item_barcode")

    @hybrid_property
    def item_title(self) -> Optional[str]:
        if self.item:
            return self.item.title
        return None

    @item_title.expression
    @classmethod
    def item_title(cls):
        from app.models.items import Item
        return (
            select(Item.title)
            .where(Item.id == cls.item_id)
            .scalar_subquery()
            .label("item_title")
        )

    # --- RELATIONSHIPS ---
    
    # Metadata Relationships
    request_type: Mapped[Optional["RequestType"]] = relationship(back_populates="requests")
    priority: Mapped[Optional["Priority"]] = relationship(back_populates="requests")
    delivery_location: Mapped[Optional["DeliveryLocation"]] = relationship(back_populates="requests")
    building: Mapped[Optional["Building"]] = relationship(back_populates="requests")
    
    # Core Relationships (Explicit Foreign Keys)
    pick_list: Mapped[Optional["PickList"]] = relationship(
        back_populates="requests",
        foreign_keys=[pick_list_id]
    )
    
    item: Mapped[Optional["Item"]] = relationship(
        back_populates="requests",
        foreign_keys=[item_id]
    )
    
    non_tray_item: Mapped[Optional["NonTrayItem"]] = relationship(
        back_populates="requests",
        foreign_keys=[non_tray_item_id]
    )
    
    batch_upload: Mapped[Optional["BatchUpload"]] = relationship(
        back_populates="requests",
        foreign_keys=[batch_upload_id]
    )
    
    requested_by: Mapped[Optional["User"]] = relationship(
        back_populates="requests",
        foreign_keys=[requested_by_id]
    )