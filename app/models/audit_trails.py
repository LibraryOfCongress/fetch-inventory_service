import sqlalchemy as sa

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from sqlalchemy import DateTime, JSON


class AuditTrail(SQLModel, table=True):
    """
    Model to represent the Audit Tails table.


    id: Optional is declared only for Python's needs before a db object is
      created. This field cannot be null in the database.
    """

    __tablename__ = "audit_log"

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    table_name: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=False, default=None)
    )
    record_id: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=False, default=None)
    )
    operation_type: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=False, default=None)
    )
    last_action: str = Field(
        sa_column=sa.Column(sa.VARCHAR(150), nullable=True, default=None)
    )
    updated_at: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    updated_by: str = Field(
        sa_column=sa.Column(sa.VARCHAR(50), nullable=False, default=None)
    )
    original_values: Optional[dict] = Field(
        sa_column=sa.Column(JSON, nullable=True, default=None)
    )
    new_values: Optional[dict] = Field(
        sa_column=sa.Column(JSON, nullable=True, default=None)
    )
