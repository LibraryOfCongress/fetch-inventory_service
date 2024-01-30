import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship


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
    user_id: Optional[int] = Field(
        sa_column=sa.Column(sa.SmallInteger, nullable=True, unique=False)
    )
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


# Association tables
class ShelvingJobTrayAssociation(SQLModel, table=True):
    verified: bool = Field(sa_column=sa.Boolean, default=False, nullable=False)
    shelf_position_proposed_id: int = Field(
        foreign_key="shelf_positions.id",
    )
    shelf_position_id: int = Field(
        foreign_key="shelf_positions.id",
    )
    shelving_job_id: int = Field(foreign_key="shelving_job.id", primary_key=True)
    tray_id: int = Field(foreign_key="tray.id", primary_key=True)


class ShelvingJobItemAssociation(SQLModel, table=True):
    verified: bool = Field(sa_column=sa.Boolean, default=False, nullable=False)
    shelf_position_proposed_id: int = Field(
        foreign_key="shelf_positions.id",
    )
    shelf_position_id: int = Field(
        foreign_key="shelf_positions.id",
    )
    shelving_job_id: int = Field(foreign_key="shelving_job.id", primary_key=True)
    item_id: int = Field(foreign_key="item.id", primary_key=True)
