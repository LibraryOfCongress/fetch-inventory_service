# /app/models/refile_jobs.py - FINAL TABLE NAME FIX

from enum import Enum
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import SmallInteger, Integer, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone, timedelta

from app.database.base import Base
from app.models.users import User

# Import the link tables for M2M
from app.models.link_tables import RefileItemTable, RefileNonTrayItemTable

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.non_tray_items import NonTrayItem 
    from app.models.items import Item
# -----------------------------------------------------


class RefileJobStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Completed = "Completed"


class RefileJob(Base): 
    """
    Model to represent refile jobs table
    """
    # CRITICAL FIX: Explicitly match the table name used in link_tables.py FKs
    __tablename__ = "refile_jobs"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(SmallInteger, primary_key=True)
    
    # Foreign Keys to User
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Run Time (timedelta -> Interval)
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=True)
    
    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            RefileJobStatus,
            nullable=False,
            name="refile_job_status_enum",
        ),
        default=RefileJobStatus.Created,
    )
    
    # Last Transition (datetime)
    last_transition: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    
    # --- RELATIONSHIPS (Many-to-Many via Link Tables) ---
    
    # Items
    items: Mapped[List["Item"]] = relationship(
        back_populates="refile_jobs", 
        secondary=RefileItemTable, # Use Table Object
        primaryjoin="RefileJob.id == refile_items.c.refile_job_id",
        secondaryjoin="Item.id == refile_items.c.item_id",         
    )
    
    # NonTrayItems
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(
        back_populates="refile_jobs", 
        secondary=RefileNonTrayItemTable, # Use Table Object
        primaryjoin="RefileJob.id == refile_non_tray_items.c.refile_job_id", 
        secondaryjoin="NonTrayItem.id == refile_non_tray_items.c.non_tray_item_id", 
    )

    # --- RELATIONSHIPS (Self-Referential User Links) ---
    
    # Assigned User
    assigned_user: Mapped[Optional["User"]] = relationship(
        back_populates="refile_jobs",
        primaryjoin="RefileJob.assigned_user_id==User.id",
        lazy="selectin"
    )

    # Created By
    created_by: Mapped[Optional["User"]] = relationship(
        back_populates="created_refile_jobs",
        primaryjoin="RefileJob.created_by_id==User.id",
        lazy="selectin"
    )