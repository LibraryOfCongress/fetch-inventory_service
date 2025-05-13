from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone

import sqlalchemy as sa

from sqlmodel import SQLModel, Field, Relationship


class BatchUploadStatus(str, Enum):
    New = "New"
    Processing = "Processing"
    Cancelled = "Cancelled"
    Failed = "Failed"
    Completed = "Completed"


class BatchUpload(SQLModel, table=True):
    """
    Model represents the batch_uploads table, to handle batch uploads from
    external sources.
    """

    __tablename__ = "batch_uploads"

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    status: str = Field(
        sa_column=sa.Column(
            sa.Enum(
                BatchUploadStatus,
                nullable=False,
                name="batch_upload_status_enum",
            )
        ),
        default=BatchUploadStatus.New,
    )
    user_id: Optional[int] = Field(foreign_key="users.id", nullable=True, default=None)
    withdraw_job_id: Optional[int] = Field(
        foreign_key="withdraw_jobs.id", nullable=True, default=None
    )
    file_name: str = Field(sa_column=sa.Column(sa.VARCHAR, nullable=False))
    file_size: int = Field(sa_column=sa.Column(sa.BigInteger, nullable=True, default=None))
    file_type: str = Field(sa_column=sa.Column(sa.VARCHAR, nullable=True, default=None))
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    requests: List["Request"] = Relationship(back_populates="batch_upload")
    withdraw_job: Optional["WithdrawJob"] = Relationship(back_populates="batch_upload")
    user: Optional["User"] = Relationship(back_populates="batch_uploads")
