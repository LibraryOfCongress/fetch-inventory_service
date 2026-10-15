# /app/models/modules.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, VARCHAR, ForeignKey, UniqueConstraint

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base
from app.models.buildings import Building # Keep this import for the relationship


class Module(Base): # <--- Inherit from Base
    """
    Model to represent the Modules table.
    Modules belong to Buildings and have a Module Number.
    """

    # NOTE: __tablename__ is handled by Base.
    # __tablename__ = "modules"

    # module_number must be unique within a building
    __table_args__ = (
        UniqueConstraint('building_id', 'module_number', name='uq_modules_building'),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key to Building
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)

    # Module Number field
    module_number: Mapped[str] = mapped_column(String(50), nullable=True)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    # building in a module (One-to-One/One-to-Many back-populating)
    building: Mapped["Building"] = relationship(back_populates="modules")
    
    # aisles in a module
    aisles: Mapped[List["Aisle"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )