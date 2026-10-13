1# /app/models/user_groups.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Integer, SmallInteger
from sqlalchemy.schema import UniqueConstraint

from typing import Optional
# REMOVED: from sqlmodel import SQLModel, Field

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class UserGroup(Base): # <--- Inherit from Base
    """
    Join table for many-to-many groups <--> users
    """

    # REMOVED: __tablename__ = "user_groups" (Handled by Base - if Base pluralization is good)
    # NOTE: Since your table name is 'user_groups' (already plural), the Base's default
    # pluralization will result in 'user_groupss'. You MUST override __tablename__.

    __tablename__ = "user_groups" # <--- OVERRIDE Base's tablename

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_user_id_group_id"),
    )

    # Primary Key - using Mapped[int] and mapped_column
    id: Mapped[Optional[int]] = mapped_column(SmallInteger, primary_key=True)

    # Foreign Keys - using Mapped[int] and ForeignKey
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)

    # CRITICAL FIX: Explicitly remove the audit columns inherited from Base
    # because the database table for this link model does not have them.
    create_dt = None
    update_dt = None