# /code/app/models/permissions.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, VARCHAR

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base
from app.models.group_permissions import GroupPermission # Dependency


class Permission(Base): # <--- Inherit from Base
    """
    Model to represent the Permissions table.
    """

    # NOTE: __tablename__ is handled by Base.
    # __tablename__ = "permissions"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Name field (unique)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    
    # Description field
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # REMOVED: create_dt and update_dt are inherited from Base

    # --- RELATIONSHIP (Many-to-Many) ---
    groups: Mapped[List["Group"]] = relationship(
        back_populates="permissions", 
        secondary=GroupPermission.__table__ # Use the __table__ attribute of the link model
    )