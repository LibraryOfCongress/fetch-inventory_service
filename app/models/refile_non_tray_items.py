from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from sqlmodel import SQLModel, Field


class RefileNonTrayItem(SQLModel, table=True):
    """
    Model to represent refile items table
    """

    __tablename__ = "refile_non_tray_items"
    __table_args__ = (
        sa.UniqueConstraint(
            "non_tray_item_id",
            "refile_job_id",
            name="uq_non_tray_item_id_refile_job_id",
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    non_tray_item_id: Optional[int] = Field(
        default=None, nullable=False, foreign_key="non_tray_items.id"
    )
    refile_job_id: Optional[int] = Field(
        default=None, nullable=False, foreign_key="refile_jobs.id"
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
