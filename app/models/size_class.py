# /app/models/size_class.py - REFACRORED TO SQLALCHEMY V2

from typing import Optional, List
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, VARCHAR, Numeric, String, Integer

from pydantic import condecimal
# REMOVED: from sqlmodel import SQLModel, Field, Relationship


# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class SizeClass(Base): # <--- Inherit from Base
    """
    Model to represent the Size Class table.
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "size_class" # NOTE: Overriding Base's default pluralization to match existing table name

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Name fields (unique)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    
    # Numeric Fields (condecimal is for Pydantic validation, actual type is Numeric)
    height: Mapped[condecimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)
    width: Mapped[condecimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)
    depth: Mapped[condecimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    trays: Mapped[List["Tray"]] = relationship(back_populates="size_class")
    items: Mapped[List["Item"]] = relationship(back_populates="size_class")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="size_class")
    shelf_types: Mapped[List["ShelfType"]] = relationship(back_populates="size_class")

    # Custom Primaryjoin Relationships
    shelving_job_discrepancies: Mapped[List["ShelvingJobDiscrepancy"]] = relationship(
        back_populates="size_class",
        primaryjoin="ShelvingJobDiscrepancy.size_class_id==SizeClass.id",
        lazy="selectin"
    )
    move_discrepancies: Mapped[List["MoveDiscrepancy"]] = relationship(
        back_populates="size_class",
        primaryjoin="MoveDiscrepancy.size_class_id==SizeClass.id",
        lazy="selectin"
    )