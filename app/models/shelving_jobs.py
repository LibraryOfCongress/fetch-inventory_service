import sqlalchemy as sa


from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.users import User


class ShelvingJobStatus(str, Enum):
    Created = "Created"
    Paused = "Paused"
    Running = "Running"
    Cancelled = "Cancelled"
    Completed = "Completed"


class OriginStatus(str, Enum):
    Verification = "Verification"
    Direct = "Direct"


class ShelvingJob(SQLModel, table=True):
    """
    Model to represent the Shelving Jobs table

    id: Optional is declared only for Python's needs before a db object is
    created. This field cannot be null in the database.
    """

    __tablename__ = "shelving_jobs"

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True), default=None)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                ShelvingJobStatus,
                name="shelving_status",
                nullable=False,
            )
        ),
        default=ShelvingJobStatus.Created,
    )
    origin: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                OriginStatus,
                name="shelving_origin",
                nullable=False,
            )
        ),
        default=OriginStatus.Verification,
    )
    building_id: int = Field(foreign_key="buildings.id", nullable=False, unique=False)
    user_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    created_by_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    run_time: Optional[timedelta] = Field(sa_column=sa.Column(sa.Interval, nullable=True))
    last_transition: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="shelving_job"
    )
    trays: List["Tray"] = Relationship(back_populates="shelving_job")
    non_tray_items: List["NonTrayItem"] = Relationship(back_populates="shelving_job")


    user: Optional[User] = Relationship(
        back_populates="shelving_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJob.user_id==User.id",
            "lazy": "selectin"
        }
    )

    created_by: Optional[User] = Relationship(
        back_populates="created_shelving_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    building: "Building" = Relationship(back_populates="shelving_jobs")

    shelving_job_discrepancies: List["ShelvingJobDiscrepancy"] = Relationship(
        back_populates="shelving_job",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJobDiscrepancy.shelving_job_id==ShelvingJob.id",
            "lazy": "selectin"
        }
    )
