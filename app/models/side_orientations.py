# /app/models/side_orientations.py - ULTIMATE, FINAL CORRECTED V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR, Integer, ForeignKey # <-- Ensure ForeignKey is imported
from sqlalchemy.schema import UniqueConstraint # <-- Ensure UniqueConstraint is imported

from typing import Optional, List
from datetime import datetime, timezone

from app.database.base import Base


class SideOrientation(Base): 
    """
    Model to represent the side orientations (Left, Right).
    """

    __tablename__ = "side_orientations"
    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Name field (unique)
    name: Mapped[str] = mapped_column(String(25), nullable=False, unique=True)
    
    # --- RELATIONSHIPS ---
    # Sides in xyz orientation
    sides: Mapped[List["Side"]] = relationship(
        back_populates="side_orientation",
        primaryjoin="Side.side_orientation_id==SideOrientation.id" # <-- FINAL FIX
    )