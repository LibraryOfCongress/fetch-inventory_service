# /app/models/verification_changes.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, Enum as SQLEnum, TIMESTAMP, ForeignKey, String, VARCHAR, CheckConstraint

from enum import Enum
from typing import Optional
from datetime import datetime, timezone
# REMOVED: from sqlmodel import SQLModel, Field, Relationship


# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class VerificationChangeStatus(str, Enum):
    """
    Enum for Verification Change Status
    """

    Added = "Added"
    Removed = "Removed"
    SizeClassEdit = "SizeClassEdit"
    MediaTypeEdit = "MediaTypeEdit"
    BarcodeValueEdit = "BarcodeValueEdit"


class VerificationChange(Base): # <--- Inherit from Base
    """
    Model to represent the Verification Changes table
    """

    # NOTE: __tablename__ is handled by Base, but we need to override it to match the migration.
    __tablename__ = "verification_changes"

    __table_args__ = (
        sa.CheckConstraint(
            "(item_barcode_value IS NOT NULL AND tray_barcode_value IS NULL) OR ("
            "item_barcode_value IS NOT NULL AND tray_barcode_value IS NOT NULL)",
            name="ck_item_xor_tray", # NOTE: This constraint looks odd (second part is redundant), but we maintain it.
        ),
    )

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)
    
    # Foreign Keys
    workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow.id"), nullable=True)
    completed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Barcode/Value Fields
    tray_barcode_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    item_barcode_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Change Type (Enum)
    change_type: Mapped[Optional[str]] = mapped_column(
        SQLEnum(
            VerificationChangeStatus,
            nullable=True,
            name="change_type",
        ),
        default=None,
    )

    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    workflow: Mapped[Optional["Workflow"]] = relationship(back_populates="verification_change")
    completed_by: Mapped[Optional["User"]] = relationship(back_populates="verification_changes")