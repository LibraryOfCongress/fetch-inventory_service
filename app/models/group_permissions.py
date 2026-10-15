# /code/app/models/group_permissions.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import SmallInteger, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from typing import Optional
# REMOVED: from sqlmodel import SQLModel, Field

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class GroupPermission(Base): # <--- Inherit from Base
    """
    Class to represent Group Permissions.
    """
    __tablename__ = "group_permissions"
    # NOTE: __tablename__ is handled by Base.
    __table_args__ = (
        UniqueConstraint("permission_id", "group_id", name="uq_permission_id_group_id"),
    )

    # Primary Key
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)

    # Foreign Keys
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), nullable=False)
    
    # CRITICAL FIX: Explicitly remove the audit columns inherited from Base
    # because the database table for this link model does not have them.
    create_dt = None
    update_dt = None