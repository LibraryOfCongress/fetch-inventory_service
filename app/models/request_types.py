# /app/models/request_types.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class RequestType(Base): # <--- Inherit from Base
    """
    Model represents the requests types table, tracks request types.
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "request_types"

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Type field (unique)
    type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, default=None)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    requests: Mapped[List["Request"]] = relationship(back_populates="request_type")