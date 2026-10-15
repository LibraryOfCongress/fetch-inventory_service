# /app/models/delivery_locations.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, VARCHAR, TIMESTAMP, DateTime, func, Column

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.requests import Request
    from app.models.owner_delivery_locations import OwnerDeliveryLocation


class DeliveryLocation(Base): # <--- Inherit from Base
    """
    Model represents delivery locations for requests.
    """

    # NOTE: __tablename__ is handled by Base, but since it's "delivery_locations" and
    # Base's default pluralization will result in "deliverylocationss", we must override.
    __tablename__ = "delivery_locations"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Name field (VARCHAR(50), unique)
    name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, default=None)

    # Address field (VARCHAR(250))
    address: Mapped[str] = mapped_column(String(250), nullable=False, unique=False, default=None)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    requests: Mapped[List["Request"]] = relationship(back_populates="delivery_location")
    
    # Owner-DeliveryLocation many-to-many relationship
    owner_delivery_locations: Mapped[List["OwnerDeliveryLocation"]] = relationship(
        back_populates="delivery_location",
        cascade="all, delete-orphan"
    )