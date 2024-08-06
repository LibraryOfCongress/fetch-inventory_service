from enum import Enum

import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.refile_items import RefileItem
from app.models.refile_non_tray_item import RefileNonTrayItem


class RefileJobStatus(str, Enum):
    Created = "Created"
    Paused = "Paused"
    Running = "Running"
    Completed = "Completed"


class RefileJob(SQLModel, table=True):
    """
    Model to represent refile jobs table
    """

    __tablename__ = "refile_jobs"

    id: Optional[int] = Field(sa_column=sa.Column(sa.SmallInteger, primary_key=True))
    assigned_user_id: Optional[int] = Field(
        default=None, foreign_key="users.id", nullable=True
    )
    run_time: Optional[timedelta] = Field(sa_column=sa.Interval, nullable=True)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                RefileJobStatus,
                nullable=False,
                name="refile_job_status_enum",
            )
        ),
        default=RefileJobStatus.Created,
    )
    last_transition: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=True
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    items: List["Item"] = Relationship(
        back_populates="refile_jobs", link_model=RefileItem
    )
    non_tray_items: List["NonTrayItem"] = Relationship(
        back_populates="refile_jobs", link_model=RefileNonTrayItem
    )
    assigned_user: Optional["User"] = Relationship(back_populates="refile_jobs")
