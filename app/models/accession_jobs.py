# /code/app/models/accession_jobs.py - FINAL CIRCULAR IMPORT FIX

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import BigInteger, Integer, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey, Boolean, select, func
from sqlalchemy.types import Enum as SQLEnum  

from typing import Optional, List, TYPE_CHECKING # <-- CRITICAL: ADD TYPE_CHECKING
from enum import Enum
from datetime import datetime, timezone, timedelta

from app.database.base import Base
# Dependencies (MUST BE IMPORTED FOR ABSOLUTE FK REFERENCE)
from app.models.container_types import ContainerType 
from app.models.media_types import MediaType 
from app.models.size_class import SizeClass 
from app.models.owners import Owner 
from app.models.users import User

# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.trays import Tray
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
    from app.models.verification_jobs import VerificationJob
    from app.models.workflows import Workflow
    from app.models.media_types import MediaType
    from app.models.size_class import SizeClass
    from app.models.container_types import ContainerType
    from app.models.owners import Owner
    from app.models.users import User
# -----------------------------------------------------

class AccessionJobStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Cancelled = "Cancelled"
    Completed = "Completed"
    Verified = "Verified"


class AccessionJob(Base): 
    
    __tablename__ = "accession_jobs"
    
    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys (CRITICAL FIX: Absolute Foreign Keys)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflow.id"))
    media_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(MediaType.__table__.c.id), nullable=True)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    size_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey(SizeClass.__table__.c.id), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Owner.__table__.c.id), nullable=True)
    container_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey(ContainerType.__table__.c.id), nullable=True)

    # Boolean
    trayed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(AccessionJobStatus, nullable=False, name="accession_status"),
        default=AccessionJobStatus.Created,
    )
    
    # Run Time (timedelta -> Interval)
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=False, default=timedelta())
    
    # Last Transition (datetime)
    last_transition: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

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
            .where(Tray.accession_job_id == cls.id)
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
            .where(Item.accession_job_id == cls.id)
            .scalar_subquery()
        )
        non_tray_subquery = (
            select(func.count(NonTrayItem.id))
            .where(NonTrayItem.accession_job_id == cls.id)
            .scalar_subquery()
        )
        return (item_subquery + non_tray_subquery).label("item_count")

    # --- RELATIONSHIPS ---
    
    container_type: Mapped[Optional["ContainerType"]] = relationship(
        back_populates="accession_jobs",
        foreign_keys="AccessionJob.container_type_id"
    )
    media_type: Mapped[Optional["MediaType"]] = relationship(
        back_populates="accession_jobs",
        foreign_keys="AccessionJob.media_type_id"
    )
    size_class: Mapped[Optional["SizeClass"]] = relationship(
        uselist=False, foreign_keys="AccessionJob.size_class_id"
    )
    owner: Mapped[Optional[Owner]] = relationship(
        back_populates="accession_jobs",
        foreign_keys="AccessionJob.owner_id"
    )
    
    # User Relationships (Custom primaryjoin)
    assigned_user: Mapped[Optional["User"]] = relationship(
        back_populates="accession_jobs",
        primaryjoin="AccessionJob.assigned_user_id==User.id",
        lazy="selectin"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        back_populates="created_accession_jobs",
        primaryjoin="AccessionJob.created_by_id==User.id",
        lazy="selectin"
    )
    
    # One-to-Many Relationships (All use string forward references)
    trays: Mapped[List["Tray"]] = relationship(
        back_populates="accession_job",
        primaryjoin="Tray.accession_job_id==AccessionJob.id"
    )
    items: Mapped[List["Item"]] = relationship(
        back_populates="accession_job",
        primaryjoin="Item.accession_job_id==AccessionJob.id"
    )
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(
        back_populates="accession_job",
        primaryjoin="NonTrayItem.accession_job_id==AccessionJob.id"
    )
    verification_jobs: Mapped[List["VerificationJob"]] = relationship(back_populates="accession_job")
    workflow: Mapped[Optional["Workflow"]] = relationship(
        back_populates="accession_job",
        foreign_keys="AccessionJob.workflow_id"
    )
