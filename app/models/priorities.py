# /app/models/priorities.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, VARCHAR

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class Priority(Base): # <--- Inherit from Base
    """
    Model represents Request priority.
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "priorities"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Value field (unique)
    value: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, default=None)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    requests: Mapped[List["Request"]] = relationship(back_populates="priority")