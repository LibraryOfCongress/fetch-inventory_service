# /app/models/pick_lists.py - FINAL CIRCULAR IMPORT FIX

from enum import Enum
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import BigInteger, Integer, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey, select, func

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone, timedelta

from app.database.base import Base
from app.models.buildings import Building 


# --- CRITICAL: DEFER IMPORTS TO BREAK CIRCULARITY ---
if TYPE_CHECKING:
    from app.models.withdraw_jobs import WithdrawJob # <--- MOVED TO DEFERRED
    from app.models.item_retrieval_events import ItemRetrievalEvent
    from app.models.non_tray_item_retrieval_events import NonTrayItemRetrievalEvent
    from app.models.users import User
    from app.models.requests import Request
# -----------------------------------------------------


class PickListStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Completed = "Completed"


class PickList(Base): 
    """
    Model to represent PickList table
    """
    __tablename__ = "pick_lists"

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys to User and Building
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    building_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Building.__table__.c.id), nullable=True)
    
    # Status (Enum)
    status: Mapped[str] = mapped_column(
        SQLEnum(PickListStatus, nullable=False, name="pick_list_status"),
        default=PickListStatus.Created,
    )
    
    # Run Time (timedelta -> Interval)
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=False, default=timedelta())
    
    # Last Transition (datetime)
    last_transition: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    # --- RAM EFFICIENT COUNTS (SQL SIDE) ---
    @hybrid_property
    def request_count(self) -> int:
        return len(self.requests)

    @request_count.expression
    @classmethod
    def request_count(cls):
        from app.models.requests import Request
        return (
            select(func.count(Request.id))
            .where(Request.pick_list_id == cls.id)
            .scalar_subquery()
            .label("request_count")
        )

    # --- RELATIONSHIPS ---
    
    # User Relationships
    assigned_user: Mapped[Optional["User"]] = relationship(
        back_populates="pick_lists",
        primaryjoin="PickList.assigned_user_id==User.id",
        lazy="selectin"
    )

    created_by: Mapped[Optional["User"]] = relationship(
        back_populates="created_pick_lists",
        primaryjoin="PickList.created_by_id==User.id",
        lazy="selectin"
    )

    # Building
    building: Mapped[Optional[Building]] = relationship(back_populates="pick_lists")
    
    # Request
    requests: Mapped[List["Request"]] = relationship(
        back_populates="pick_list",
        primaryjoin="Request.pick_list_id==PickList.id"
    )
    
    # WithdrawJob
    # Uses string reference "WithdrawJob" and string primaryjoin, so deferred import is safe
    withdraw_jobs: Mapped[List["WithdrawJob"]] = relationship(
        back_populates="pick_list",
        primaryjoin="WithdrawJob.pick_list_id==PickList.id" 
    )
    
    # Other relationships
    items_retrieval_events: Mapped[List["ItemRetrievalEvent"]] = relationship(back_populates="pick_list")
    non_tray_items_retrieval_events: Mapped[List["NonTrayItemRetrievalEvent"]] = (
        relationship(back_populates="pick_list")
    )