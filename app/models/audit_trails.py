# /code/app/models/audit_trails.py - Updated for app-level audit logging

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import BigInteger, TIMESTAMP, JSON, String

from typing import Optional
from datetime import datetime, timezone


# Separate DeclarativeBase since this table has a custom schema (no create_dt)
class AuditTrailBase(DeclarativeBase):
    pass


class AuditTrail(AuditTrailBase):
    """
    Model for the audit_log table.
    Stores application-level audit events for jobs and entities.
    """

    __tablename__ = "audit_log"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # --- Legacy columns (kept for backward compat, now nullable) ---
    table_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    record_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    operation_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    last_action: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, default=None)

    # --- New app-level audit columns ---
    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    job_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    job_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)

    # Timestamp
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )

    # User info
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)

    # JSON Fields
    original_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)