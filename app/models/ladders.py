# /app/models/ladders.py - REFACTORED: Removed LadderNumber lookup table dependency

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, SmallInteger, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from typing import Optional, List
from datetime import datetime, timezone
from app.database.base import Base

# Dependencies
from app.models.sides import Side


class Ladder(Base):
    """
    Model to represent Ladders table
    """

    # NOTE: __tablename__ is handled by Base.
    __table_args__ = (
        UniqueConstraint(
            "side_id", "ladder_number", name="uq_side_id_ladder_number"
        ),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Direct integer column (replaces ladder_number_id FK)
    ladder_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Foreign Keys
    side_id: Mapped[int] = mapped_column(ForeignKey("sides.id"), nullable=False)

    # Sort Priority
    sort_priority: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, default=None)
    
    # --- RELATIONSHIPS ---
    side: Mapped[Side] = relationship(back_populates="ladders")
    shelves: Mapped[List["Shelf"]] = relationship(
        back_populates="ladder",
        cascade="all, delete-orphan"
    )