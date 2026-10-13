# /code/app/models/media_types.py - FINAL CORRECTED V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR, Integer

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.items import Item
    from app.models.trays import Tray # <--- ADDED
    from app.models.non_tray_items import NonTrayItem # <--- ADDED
    from app.models.accession_jobs import AccessionJob
    from app.models.verification_jobs import VerificationJob
# -----------------------------------------------------

class MediaType(Base): 
    """
    Model to represent the Media Type table.
    """
    # Explicit table name is good practice given the issues we've seen
    __tablename__ = "media_types"

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Name field (unique)
    name: Mapped[str] = mapped_column(String(25), nullable=False, unique=True)
    
    # --- RELATIONSHIPS ---
    
    # Jobs
    accession_jobs: Mapped[List["AccessionJob"]] = relationship(back_populates="media_type")
    
    verification_jobs: Mapped[List["VerificationJob"]] = relationship(
        back_populates="media_type"
    )
    
    # Items/Containers
    items: Mapped[List["Item"]] = relationship(back_populates="media_type")
    
    # CRITICAL FIX: Add missing inverse relationships for Tray and NonTrayItem
    trays: Mapped[List["Tray"]] = relationship(back_populates="media_type")
    
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="media_type")