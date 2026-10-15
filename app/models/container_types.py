# /app/models/container_types.py - FINAL CORRECTED V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR, Integer

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

from app.database.base import Base

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.shelves import Shelf
    from app.models.accession_jobs import AccessionJob
    from app.models.verification_jobs import VerificationJob
    from app.models.move_discrepancies import MoveDiscrepancy
    from app.models.trays import Tray # <--- ADDED
    from app.models.non_tray_items import NonTrayItem # <--- ADDED
# -----------------------------------------------------


class ContainerType(Base): 
    """
    Model to represent container types.
    """
    # Explicit table name to ensure FK strings work
    __tablename__ = "container_types"

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Type field
    type: Mapped[str] = mapped_column(String(25), nullable=False, unique=True)
    
    # --- RELATIONSHIPS ---
    
    # Shelves
    shelves: Mapped[List["Shelf"]] = relationship(back_populates="container_type")
    
    # Accession Jobs
    accession_jobs: Mapped[List["AccessionJob"]] = relationship(
        back_populates="container_type",
        primaryjoin="AccessionJob.container_type_id==ContainerType.id",
    )
    
    # Verification Jobs
    verification_jobs: Mapped[List["VerificationJob"]] = relationship(
        back_populates="container_type",
        primaryjoin="VerificationJob.container_type_id==ContainerType.id",
    )
    
    # Move Discrepancies
    move_discrepancies: Mapped[List["MoveDiscrepancy"]] = relationship(
        back_populates="container_type",
        primaryjoin="MoveDiscrepancy.container_type_id==ContainerType.id",
        lazy="selectin"
    )

    # CRITICAL FIX: Add missing inverse relationships for Tray and NonTrayItem
    trays: Mapped[List["Tray"]] = relationship(back_populates="container_type")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="container_type")