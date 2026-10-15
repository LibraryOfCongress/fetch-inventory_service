# /app/models/barcodes.py - FINAL, UNBREAKABLE FIX FOR AmbiguousForeignKeysError

import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from sqlalchemy import BigInteger, VARCHAR, TIMESTAMP, ForeignKey, Boolean, Integer, String, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from typing import Optional, List
from datetime import datetime, timezone
from app.database.base import Base 
from app.models.barcode_types import BarcodeType # Imported for the unbreakable FK


class Barcode(Base): # <--- Inherit from Base
    """
    Model to represent the Barcode table.
    """

    # --- CORE FIELDS ---
    id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=None,
        server_default=text("gen_random_uuid()")
    )
    
    value: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        unique=True
    )
    
    withdrawn: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Foreign Key to BarcodeType
    # CRITICAL FIX: Use BarcodeType.__table__.c.id for explicit, unbreakable reference
    type_id: Mapped[int] = mapped_column(
        ForeignKey(BarcodeType.__table__.c.id), 
        nullable=False
    )
    
    # --- RELATIONSHIPS ---

    # Problem relationship: fixed with explicit foreign_keys list
    type: Mapped[Optional["BarcodeType"]] = relationship(
        back_populates="barcodes",
        foreign_keys=[type_id] 
    )

    # --- INVERSE RELATIONSHIPS (CRITICAL AMBIGUITY FIX) ---
    # NOTE: primaryjoin is used to explicitly tell SQLAlchemy which FK to use.
    
    barcode_item: Mapped[List["Item"]] = relationship(
        back_populates="barcode", 
        viewonly=True, 
        uselist=False,
        primaryjoin="Item.barcode_id==Barcode.id"
    )
    withdrawn_item: Mapped[List["Item"]] = relationship(
        back_populates="withdrawn_barcode", 
        viewonly=True, 
        uselist=False,
        primaryjoin="Item.withdrawn_barcode_id==Barcode.id"
    )
    barcode_tray: Mapped[List["Tray"]] = relationship(
        back_populates="barcode", viewonly=True, uselist=False,
        primaryjoin="Tray.barcode_id==Barcode.id"
    )
    withdrawn_tray: Mapped[List["Tray"]] = relationship(
        back_populates="withdrawn_barcode", viewonly=True, uselist=False,
        primaryjoin="Tray.withdrawn_barcode_id==Barcode.id"
    )
    barcode_non_tray_item: Mapped[List["NonTrayItem"]] = relationship(
        back_populates="barcode", viewonly=True, uselist=False,
        primaryjoin="NonTrayItem.barcode_id==Barcode.id"
    )
    withdrawn_non_tray_item: Mapped[List["NonTrayItem"]] = relationship(
        back_populates="withdrawn_barcode", viewonly=True, uselist=False,
        primaryjoin="NonTrayItem.withdrawn_barcode_id==Barcode.id"
    )