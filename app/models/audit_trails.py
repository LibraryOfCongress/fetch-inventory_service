import sqlalchemy as sa

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, JSON


class AuditTrail(SQLModel, table=True):
    """
    Model to represent the Audit Tails table.


    id: Optional is declared only for Python's needs before a db object is
      created. This field cannot be null in the database.
    """

    __tablename__ = "audit_log"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    table_name: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, default=None
    )
    record_id: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, default=None
    )
    operation_type: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, default=None
    )
    last_action: str = Field(
        max_length=150, sa_column=sa.VARCHAR, nullable=True, default=None
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    updated_by: str = Field(
        max_length=50, sa_column=sa.VARCHAR, nullable=False, default=None
    )
    original_values: Optional[dict] = Field(
        sa_column=sa.Column(JSON, nullable=True), default=None
    )
    new_values: Optional[dict] = Field(
        sa_column=sa.Column(JSON, nullable=True), default=None
    )
