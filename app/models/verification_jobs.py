# /app/models/verification_jobs.py - ULTIMATE, FINAL CORRECTED V2

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import BigInteger, Integer, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey, Boolean, select, func
from sqlalchemy.types import Enum as SQLEnum  # Safety import

from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from datetime import datetime, timezone, timedelta

from app.database.base import Base
# Dependencies (MUST BE IMPORTED FOR ABSOLUTE FK REFERENCE)
from app.models.accession_jobs import AccessionJob
from app.models.owners import Owner
from app.models.container_types import ContainerType 
from app.models.media_types import MediaType
from app.models.size_class import SizeClass
from app.models.users import User
from app.models.shelving_jobs import ShelvingJob # <--- CRITICAL IMPORT

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.trays import Tray
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
    from app.models.workflows import Workflow
    
# -----------------------------------------------------


class VerificationJobStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Completed = "Completed"


class VerificationJob(Base): 

    __tablename__ = "verification_jobs"
    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys (CRITICAL FIX: Absolute Foreign Keys)
    workflow_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow.id"), nullable=True)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    accession_job_id: Mapped[int] = mapped_column(ForeignKey(AccessionJob.__table__.c.id), nullable=False) # FK to AccessionJob

    # CRITICAL FIXES: ABSOLUTE FOREIGN KEY REFERENCES
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True) 
    media_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(MediaType.__table__.c.id), nullable=True) 
    size_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=True)
    
    # Standard FKs 
    # CRITICAL FIX: Use ShelvingJob.__table__.c.id for explicit, unbreakable reference
    shelving_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ShelvingJob.__table__.c.id), nullable=True) # <-- THE FINAL FK FIX


    # Boolean
    trayed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(
            VerificationJobStatus,
            name="verification_status",
        ),
        default=VerificationJobStatus.Created,
    )
    
    # Run Time (timedelta -> Interval)
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=False, default=timedelta())
    
    # Last Transition (datetime)
    last_transition: Mapped[datetime] = mapped_column(
    TIMESTAMP(timezone=True), 
    nullable=False, 
    default=lambda: datetime.now(timezone.utc)
)


    # --- RAM EFFICIENT COUNTS (SQL SIDE) ---
    @hybrid_property
    def tray_count(self) -> int:
        return len(self.trays)

    @tray_count.expression
    @classmethod
    def tray_count(cls):
        from app.models.trays import Tray
        return (
            select(func.count(Tray.id))
            .where(Tray.verification_job_id == cls.id)
            .scalar_subquery()
            .label("tray_count")
        )

    @hybrid_property
    def item_count(self) -> int:
        return len(self.items) + len(self.non_tray_items)

    @item_count.expression
    @classmethod
    def item_count(cls):
        from app.models.items import Item
        from app.models.non_tray_items import NonTrayItem
        item_subquery = (
            select(func.count(Item.id))
            .where(Item.verification_job_id == cls.id)
            .scalar_subquery()
        )
        non_tray_subquery = (
            select(func.count(NonTrayItem.id))
            .where(NonTrayItem.verification_job_id == cls.id)
            .scalar_subquery()
        )
        return (item_subquery + non_tray_subquery).label("item_count")

    # --- RELATIONSHIPS ---
    
    # 1. Owner
    owner: Mapped[Optional[Owner]] = relationship(
        back_populates="verification_jobs",
        foreign_keys=[owner_id]
    )
    # 2. Media Type
    media_type: Mapped[Optional[MediaType]] = relationship(
        back_populates="verification_jobs",
        foreign_keys=[media_type_id]
    )
    # 3. Size Class
    size_class: Mapped[Optional["SizeClass"]] = relationship(
        uselist=False, 
        foreign_keys=[size_class_id]
    )
    # 4. Container Type
    container_type: Mapped[Optional[ContainerType]] = relationship(
        back_populates="verification_jobs",
        foreign_keys=[container_type_id] 
    )
    
    # 5. Shelving Job
    # FINAL FIX: Use primaryjoin to resolve the ambiguity
    shelving_job: Mapped[Optional["ShelvingJob"]] = relationship(
        back_populates="verification_jobs",
        primaryjoin="VerificationJob.shelving_job_id==ShelvingJob.id" # <-- FINAL FIX for the current error
    )
    
    # User Relationships (Custom primaryjoin)
    assigned_user: Mapped[Optional["User"]] = relationship(
        back_populates="verification_jobs",
        primaryjoin="VerificationJob.assigned_user_id==User.id",
        lazy="selectin"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        back_populates="created_verification_jobs",
        primaryjoin="VerificationJob.created_by_id==User.id",
        lazy="selectin"
    )

    # Standard One-to-One / One-to-Many Relationships (string forward references are safe)
    accession_job: Mapped["AccessionJob"] = relationship(back_populates="verification_jobs")
    workflow: Mapped[Optional["Workflow"]] = relationship(back_populates="verification_job")

    # One-to-Many Relationships (string forward references are safe)
    trays: Mapped[List["Tray"]] = relationship(back_populates="verification_job")
    items: Mapped[List["Item"]] = relationship(back_populates="verification_job")
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(back_populates="verification_job")