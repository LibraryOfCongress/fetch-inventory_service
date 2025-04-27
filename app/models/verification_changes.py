from enum import Enum
from typing import Optional
from datetime import datetime, timezone

import sqlalchemy as sa

from sqlmodel import SQLModel, Field, Relationship


class VerificationChangeStatus(str, Enum):
    """
    Enum for Verification Change Status
    """

    Added = "Added"
    Removed = "Removed"
    SizeClassEdit = "SizeClassEdit"
    MediaTypeEdit = "MediaTypeEdit"
    BarcodeValueEdit = "BarcodeValueEdit"


class VerificationChange(SQLModel, table=True):
    """
    Model to represent the Verification Changes table
    """

    __tablename__ = "verification_changes"
    __table_args__ = (
        sa.CheckConstraint(
            "(item_barcode_value IS NOT NULL AND tray_barcode_value IS NULL) OR ("
            "item_barcode_value IS NOT NULL AND tray_barcode_value IS NOT NULL)",
            name="ck_item_xor_tray",
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    workflow_id: Optional[int] = Field(foreign_key="workflow.id", nullable=True)
    tray_barcode_value: Optional[str] = Field(default=None, nullable=True, unique=False)
    item_barcode_value: Optional[str] = Field(default=None, nullable=True, unique=False)
    change_type: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                VerificationChangeStatus,
                nullable=True,
                name="change_type",
            )
        ),
        default=None,
    )
    completed_by_id: Optional[int] = Field(default=None, foreign_key="users.id",
                                        nullable=True)
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    workflow: Optional["Workflow"] = Relationship(back_populates="verification_change")
    completed_by: Optional["User"] = Relationship(back_populates="verification_changes")
