import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.users import User


class ShelvingJob(SQLModel, table=True):
    """
    Model to represent the Shelving Jobs table

    id: Optional is declared only for Python's needs before a db object is
    created. This field cannot be null in the database.
    """

    __tablename__ = "shelving_jobs"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.Integer, default=None)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                "Created",
                "Paused",
                "Running",
                "Cancelled",
                "Completed",
                name="shelving_status",
            )
        ),
        default="Created",
        nullable=False,
    )
    origin: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                "Verification",
                "Direct",
                name="shelving_origin",
            )
        ),
        default="Verification",
        nullable=False,
    )
    building_id: int = Field(foreign_key="buildings.id", nullable=False, unique=False)
    user_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    run_time: Optional[timedelta] = Field(sa_column=sa.Interval, nullable=True)
    last_transition: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=True
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="shelving_job"
    )
    trays: List["Tray"] = Relationship(back_populates="shelving_job")
    non_tray_items: List["NonTrayItem"] = Relationship(back_populates="shelving_job")
    user: Optional[User] = Relationship(back_populates="shelving_jobs")
    building: "Building" = Relationship(back_populates="shelving_jobs")
