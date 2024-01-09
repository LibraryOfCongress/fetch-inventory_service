import sqlalchemy as sa

from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Relationship

from app.models.owners import Owner
from app.models.container_types import ContainerType


class VerificationJob(SQLModel, table=True):
    """
    Model to represent the Verification Jobs table.
    Verification Jobs are used for ingesting new items, trays, and
    non-trayed items into the database.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "verification_jobs"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    trayed: bool = Field(sa_column=sa.Boolean, default=True, nullable=False)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                "Created",
                "Paused",
                "Running",
                "Cancelled",
                "Completed",
                name="verification_status",
            )
        ),
        default="Created",
        nullable=False,
    )
    # TODO: for user_id FK to users table later
    user_id: Optional[int] = Field(
        sa_column=sa.Column(
            sa.SmallInteger,
        )
    )
    last_transition: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=True
    )
    run_time: Optional[timedelta] = Field(sa_column=sa.Interval(6), nullable=True)
    accession_job_id: Optional[int] = Field(
        sa_column=sa.Column(
            sa.BigInteger, sa.ForeignKey("accession_jobs.id"), nullable=False
        )
    )
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )

    owner: Owner = Relationship(back_populates="verification_jobs")
    container_type: ContainerType = Relationship(back_populates="verification_jobs")


# TODO: Tray, Non-Tray, and Item models to be add relationships to the
#  VerificationJob model
# Tray.verification_job_id (big integer) nullable foreign key relationship to VerificationJob.id
# Item.verification_job_id (big integer) nullable foreign key relationship to VerificationJob.id
