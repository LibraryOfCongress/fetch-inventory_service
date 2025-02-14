from enum import Enum

import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.refile_items import RefileItem
from app.models.refile_non_tray_items import RefileNonTrayItem


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
    created_by_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    run_time: Optional[timedelta] = Field(sa_column=sa.Column(sa.Interval, nullable=True))
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
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    items: List["Item"] = Relationship(
        back_populates="refile_jobs", link_model=RefileItem
    )
    non_tray_items: List["NonTrayItem"] = Relationship(
        back_populates="refile_jobs", link_model=RefileNonTrayItem
    )

    assigned_user: Optional["User"] = Relationship(
        back_populates="refile_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "RefileJob.assigned_user_id==User.id",
            "lazy": "selectin"
        }
    )

    created_by: Optional["User"] = Relationship(
        back_populates="created_refile_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "RefileJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )
