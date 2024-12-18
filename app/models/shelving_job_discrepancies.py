import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime


class ShelvingJobDiscrepancy(SQLModel, table=True):
    __tablename__ = "shelving_job_discrepancies"
    __table_args__ = (
        sa.CheckConstraint(
            "(tray_id IS NOT NULL) OR (non_tray_item_id IS NOT NULL)",
            name="ck_s_discrepancy_tray_xor_non_tray",
        ),
    )

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    shelving_job_id: int = Field(foreign_key="shelving_jobs.id", nullable=False, unique=False)
    tray_id: Optional[int] = Field(foreign_key="trays.id", nullable=True, unique=False)
    non_tray_item_id: Optional[int] = Field(foreign_key="non_tray_items.id", nullable=True, unique=False)
    user_id: int = Field(foreign_key="users.id", nullable=True, unique=False)
    error: Optional[str] = Field(
        max_length=350, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    shelving_job: Optional["ShelvingJob"] = Relationship(back_populates="shelving_job_discrepancies")
    tray: Optional["Tray"] = Relationship(back_populates="shelving_job_discrepancies")
    non_tray_item: Optional["NonTrayItem"] = Relationship(back_populates="shelving_job_discrepancies")
    user: Optional["User"] = Relationship(back_populates="shelving_job_discrepancies")
