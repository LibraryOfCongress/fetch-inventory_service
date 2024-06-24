import sqlalchemy as sa

from typing import Optional
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field


class RefileNonTrayItem(SQLModel, table=True):
    """
    Model to represent refile items table
    """

    __tablename__ = "refile_non_tray_items"
    __table_args__ = (
        UniqueConstraint(
            "non_tray_item_id",
            "refile_job_id",
            name="uq_non_tray_item_id_refile_job_id",
        ),
    )
    non_tray_item_id: Optional[int] = Field(
        foreign_key="non_tray_items.id", nullable=False, primary_key=True
    )
    refile_job_id: Optional[int] = Field(
        default=None, foreign_key="refile_jobs.id", nullable=True
    )
