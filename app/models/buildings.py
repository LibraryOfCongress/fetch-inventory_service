# /app/models/buildings.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, Integer, TIMESTAMP, DateTime, func, Column, VARCHAR

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class Building(Base): # <--- Inherit from Base
    """
    Model to represent the buildings table.
    """

    # REMOVED: __tablename__ = "buildings" (Handled by Base)

    # Primary Key - using Mapped[int]
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Name field
    name: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, default=None)

    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    # modules in a building
    modules: Mapped[List["Module"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan"
    )
    shelving_jobs: Mapped[List["ShelvingJob"]] = relationship(back_populates="building")
    pick_lists: Mapped[List["PickList"]] = relationship(back_populates="building")
    requests: Mapped[List["Request"]] = relationship(back_populates="building")
    # Per-ILSConfiguration FOLIO service point overrides for this physical
    # building. See app.models.building_ils_service_points.
    ils_service_points: Mapped[List["BuildingILSServicePoint"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan"
    )
