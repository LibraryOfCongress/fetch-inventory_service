# /code/app/models/batch_upload.py - REFACRORED TO SQLALCHEMY V2

from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, VARCHAR, ForeignKey, Enum as SQLEnum, String, Integer, JSON

# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base


class BatchUploadStatus(str, Enum):
    New = "New"
    Processing = "Processing"
    Cancelled = "Cancelled"
    Failed = "Failed"

    Uploaded = "Uploaded"
    Completed = "Completed"


class BatchUpload(Base): # <--- Inherit from Base
    """
    Model represents the batch_uploads table.
    """

    # NOTE: __tablename__ is handled by Base, BUT we need snake_case for multi-word models
    __tablename__ = "batch_uploads"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            BatchUploadStatus,
            nullable=False,
            name="batch_upload_status_enum", # MUST match DB type name
        ),
        default=BatchUploadStatus.New,
    )

    # Foreign Keys
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    withdraw_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("withdraw_jobs.id"), nullable=True)
    
    # File Metadata Fields
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, default=None)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True, default=None)

    # Outcome of async processing (set by the background task):
    # {"message": str, "shelves_created": int, "error_count": int, "errors": [{line, error}]}
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    
    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RELATIONSHIPS ---
    requests: Mapped[List["Request"]] = relationship(back_populates="batch_upload")
    withdraw_job: Mapped[Optional["WithdrawJob"]] = relationship(back_populates="batch_upload")
    user: Mapped[Optional["User"]] = relationship(back_populates="batch_uploads")