# /app/models/sides.py - FULLY CORRECTED REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.schema import UniqueConstraint # <--- CRITICAL FIX: Missing import added

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base
from app.models.aisles import Aisle
from app.models.side_orientations import SideOrientation


class Side(Base): # <--- Inherit from Base
    """
    Model to represent the sides table.
    """

    # NOTE: __tablename__ is handled by Base.
    __table_args__ = (
        UniqueConstraint(
            "aisle_id", "side_orientation_id", name="uq_aisle_id_side_orientation_id"
        ),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    aisle_id: Mapped[int] = mapped_column(ForeignKey(Aisle.__table__.c.id), nullable=False)
    side_orientation_id: Mapped[int] = mapped_column(ForeignKey(SideOrientation.__table__.c.id), nullable=False)

    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    # side orientation belonging to a side
    side_orientation: Mapped[SideOrientation] = relationship(back_populates="sides")
    
    # aisle in which the side is located
    aisle: Mapped[Aisle] = relationship(back_populates="sides")
    
    # Ladders on a side
    ladders: Mapped[List["Ladder"]] = relationship(
        back_populates="side",
        cascade="all, delete-orphan"
    )