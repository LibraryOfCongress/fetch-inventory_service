# /app/models/shelving_jobs.py - REFACRORED TO SQLALCHEMY V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property # Added hybrid_property
from sqlalchemy import Integer, Boolean, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey, select, func # Added select and func

from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone, timedelta
# REMOVED: from sqlmodel import SQLModel, Field, Relationship

# NEW IMPORT: Import the Base class you created
from app.database.base import Base
from app.models.users import User


if TYPE_CHECKING:
    from app.models.verification_jobs import VerificationJob
    from app.models.trays import Tray
    from app.models.non_tray_items import NonTrayItem
    from app.models.buildings import Building
    from app.models.users import User
    from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
    from app.models.shelving_job_containers import ShelvingJobContainer

class ShelvingJobStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Cancelled = "Cancelled"
    Completed = "Completed"


class OriginStatus(str, Enum):
    Verification = "Verification"  # Legacy - kept for existing data
    Direct = "Direct"
    List = "List"
    Move = "Move"  # NEW: Move Operations


class ShelvingMode(str, Enum):
    """Mode determines how the shelving job is executed."""
    Manual = "Manual"        # User scans shelf then container
    PreAssigned = "PreAssigned"  # System assigns, user follows directions
    MoveTrayItem = "MoveTrayItem" # Item -> Tray
    MoveShelf = "MoveShelf" # Tray/Item -> Shelf


class ShelvingJob(Base): # <--- Inherit from Base
    """
    Model to represent the Shelving Jobs table
    """

    # NOTE: __tablename__ is handled by Base.
    __tablename__ = "shelving_jobs"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True)

    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            ShelvingJobStatus,
            name="shelving_status",
            nullable=False,
        ),
        default=ShelvingJobStatus.Created,
    )

    # Origin (Enum)
    origin: Mapped[str] = mapped_column(
        SQLEnum(
            OriginStatus,
            name="shelving_origin",
            nullable=False,
            create_constraint=False,  # Allow adding new values via migration
        ),
        default=OriginStatus.Verification,
    )

    # NEW: Mode (Enum) - How the job is executed (for List origin jobs)
    mode: Mapped[Optional[str]] = mapped_column(
        SQLEnum(
            ShelvingMode,
            name="shelving_mode",
            nullable=True,
        ),
        nullable=True,
        default=None,
    )

    # NEW: Pre-assignment configuration flags (for List origin jobs)
    allow_unassigned_size: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_unassigned_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_tiered_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Foreign Keys
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Run Time (timedelta -> Interval)
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=True)
    
    # Last Transition (datetime)
    last_transition: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    # REMOVED: create_dt and update_dt are handled by the Base class.

    # --- RAM EFFICIENT COUNTS (SQL SIDE) ---
    @hybrid_property
    def tray_count(self) -> int:
        return len(self.trays)

    @tray_count.expression
    @classmethod
    def tray_count(cls):
        from app.models.trays import Tray
        return (
            select(func.count(sa.text("*")))
            .where(Tray.shelving_job_id == cls.id)
            .scalar_subquery()
            .label("tray_count")
        )

    @hybrid_property
    def non_tray_item_count(self) -> int:
        return len(self.non_tray_items)

    @non_tray_item_count.expression
    @classmethod
    def non_tray_item_count(cls):
        from app.models.non_tray_items import NonTrayItem
        return (
            select(func.count(sa.text("*")))
            .where(NonTrayItem.shelving_job_id == cls.id)
            .scalar_subquery()
            .label("non_tray_item_count")
        )

    @hybrid_property
    def container_count(self) -> int:
        return self.tray_count + self.non_tray_item_count

    @container_count.expression
    @classmethod
    def container_count(cls):
        return cls.tray_count + cls.non_tray_item_count

    # --- RELATIONSHIPS ---

    # User Relationships (Custom primaryjoin)
    assigned_user: Mapped[Optional[User]] = relationship(
        back_populates="shelving_jobs",
        primaryjoin="ShelvingJob.assigned_user_id==User.id",
        lazy="selectin"
    )
    created_by: Mapped[Optional[User]] = relationship(
        back_populates="created_shelving_jobs",
        primaryjoin="ShelvingJob.created_by_id==User.id",
        lazy="selectin"
    )

    # Standard One-to-Many Relationships
    verification_jobs: Mapped[List["VerificationJob"]] = relationship(back_populates="shelving_job")
    trays: Mapped[List["Tray"]] = relationship(back_populates="shelving_job")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="shelving_job")
    building: Mapped["Building"] = relationship(back_populates="shelving_jobs")
    shelving_job_discrepancies: Mapped[List["ShelvingJobDiscrepancy"]] = relationship(
        back_populates="shelving_job",
        primaryjoin="ShelvingJobDiscrepancy.shelving_job_id==ShelvingJob.id",
        lazy="selectin"
    )
    
    # NEW: Relationship to ShelvingJobContainer (for List origin jobs)
    shelving_job_containers: Mapped[List["ShelvingJobContainer"]] = relationship(
        back_populates="shelving_job",
        lazy="selectin"
    )