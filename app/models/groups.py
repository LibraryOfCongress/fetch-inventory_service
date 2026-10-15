# /code/app/models/groups.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, String, VARCHAR, Integer

from typing import Optional, List
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base
from app.models.user_groups import UserGroup
from app.models.group_permissions import GroupPermission


class Group(Base): # <--- Inherit from Base
    """
    Class to represent user Groups.
    """

    # NOTE: __tablename__ is handled by Base.
    # __tablename__ = "groups"

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    
    # Name field (unique)
    name: Mapped[str] = mapped_column(String(75), nullable=False, unique=True)
    
    # REMOVED: create_dt and update_dt are inherited from Base

    # --- RELATIONSHIPS (Many-to-Many) ---

    # 1. Users M2M
    users: Mapped[List["User"]] = relationship(
        back_populates="groups", 
        secondary=UserGroup.__table__ # Use the __table__ attribute of the link model
    )
    
    # 2. Permissions M2M
    permissions: Mapped[List["Permission"]] = relationship(
        back_populates="groups", 
        secondary=GroupPermission.__table__ # Use the __table__ attribute of the link model
    )