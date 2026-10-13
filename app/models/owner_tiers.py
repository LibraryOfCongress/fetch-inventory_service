# /app/models/owner_tiers.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR, Integer

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class OwnerTier(Base): # <--- Inherit from Base
    """
    Model to represent Owner Tiers table
    """

  
    __tablename__ = "owner_tiers"

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Level field (unique)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True, default=None)

    # Name field (unique)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, default=None)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    # owners assigned this tier
    owners: Mapped[List["Owner"]] = relationship(back_populates="owner_tier")