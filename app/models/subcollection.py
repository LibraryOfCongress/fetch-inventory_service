# /code/app/models/subcollection.py - FINAL CIRCULAR IMPORT FIX

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, VARCHAR, Integer

from typing import Optional, List, TYPE_CHECKING # <-- CRITICAL: ADD TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
# Only need to defer models that have an import path back to this file
if TYPE_CHECKING:
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
# -----------------------------------------------------


class Subcollection(Base): # <--- Inherit from Base
    """
    Model to represent the Subcollections table.
    """

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)
    
    # Name field (unique)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    
    # --- RELATIONSHIPS ---
    items: Mapped[List["Item"]] = relationship(back_populates="subcollection")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="subcollection")