# /app/models/shelf_types.py - ULTIMATE, FINAL CORRECTED V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR, Integer, ForeignKey

from typing import Optional, List
from datetime import datetime, timezone

from app.database.base import Base


class ShelfType(Base): 
    """
    Model to represent Shelf Types table
    """

    __tablename__ = "shelf_types"
    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Type field (unique)
    type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    
    # Foreign Key to SizeClass
    size_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("size_class.id"), nullable=False) # NOTE: Assuming SizeClass FK is string-based for simplicity here

    # Max Capacity
    max_capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # --- RELATIONSHIPS ---
    size_class: Mapped["SizeClass"] = relationship(back_populates="shelf_types")
    
    # CRITICAL FIX: Add primaryjoin
    shelves: Mapped[List["Shelf"]] = relationship(
        back_populates="shelf_type",
        primaryjoin="Shelf.shelf_type_id==ShelfType.id" # <-- FINAL FIX
    )