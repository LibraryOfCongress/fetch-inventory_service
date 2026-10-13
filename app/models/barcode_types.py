# /code/app/models/barcode_types.py - FINAL CORRECTED REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
# CRITICAL FIX: Ensure all needed types are imported
from sqlalchemy import SmallInteger, String, Integer, ForeignKey # <-- ADDED ForeignKey

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class BarcodeType(Base): # <--- Inherit from Base
    """
    Model to represent the Barcode Type table.
    """

  
    __tablename__ = "barcode_types"

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Name field (unique)
    name: Mapped[str] = mapped_column(String(25), nullable=False, unique=True)
    
    # Allowed Pattern
    allowed_pattern: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        index=True,
        default="^.{25}$",
    )
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIP ---
    barcodes: Mapped[List["Barcode"]] = relationship(
        back_populates="type",
        # CRITICAL FIX: Use explicit primaryjoin to tell it how to join
        # This tells BarcodeType to look for the FK (type_id) in the Barcode table
        primaryjoin="Barcode.type_id==BarcodeType.id",
    )