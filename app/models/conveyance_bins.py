# /code/app/models/conveyance_bins.py - REFACRORED TO SQLALCHEMY V2

import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class ConveyanceBin(Base): # <--- Inherit from Base
    """
    Model to represent the Conveyance Bin table.
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "conveyance_bins"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True)

    # Foreign Key (UUID)
    barcode_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("barcodes.id"),
        nullable=False,
        unique=True,
        default=None,
    )
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    trays: Mapped[List["Tray"]] = relationship(back_populates="conveyance_bin")
    barcode: Mapped[Optional["Barcode"]] = relationship(
        uselist=False # One-to-One relationship
    )