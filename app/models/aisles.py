# /app/models/aisles.py - REFACTORED: Removed AisleNumber lookup table dependency

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, SmallInteger, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from typing import Optional, List
from datetime import datetime, timezone

from app.database.base import Base
from app.models.modules import Module


class Aisle(Base):
    """
    Model to represent the aisles table.
    """

    # NOTE: __tablename__ is handled by Base.

    __table_args__ = (
        UniqueConstraint(
            "module_id", "aisle_number", name="uq_module_aisle_number"
        ),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sort Priority
    sort_priority: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, default=None)

    # Direct integer column (replaces aisle_number_id FK)
    aisle_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Foreign Keys
    module_id: Mapped[Optional[int]] = mapped_column(ForeignKey("modules.id"), nullable=True, default=None)
    
    # --- RELATIONSHIPS ---
    # module belonging to an aisle
    module: Mapped[Optional[Module]] = relationship(back_populates="aisles")
    
    # sides belonging to an aisle
    sides: Mapped[List["Side"]] = relationship(
        back_populates="aisle",
        cascade="all, delete-orphan"
    )