# /app/models/withdraw_jobs.py - FINAL FIX FOR PICKLIST FK

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, Enum as SQLEnum, Interval, TIMESTAMP, ForeignKey

from app.database.base import Base
from app.models.users import User 

# --- CRITICAL: IMPORT TABLE OBJECTS ---
from app.models.link_tables import (
    ItemWithdrawalTable, 
    NonTrayItemWithdrawalTable, 
    TrayWithdrawalTable
)

# --- CRITICAL: RUNTIME IMPORT FOR ABSOLUTE FK ---
# We import PickList here to use PickList.__table__.c.id. 
# This is safe because PickList defers its import of WithdrawJob.
from app.models.pick_lists import PickList 

# --- CRITICAL: DEFER OTHER CIRCULAR MODELS ---
if TYPE_CHECKING:
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
    from app.models.trays import Tray
    from app.models.batch_upload import BatchUpload
# -----------------------------------------------------

class WithdrawJobStatus(str, Enum):
    Created = "Created"
    Assigned = "Assigned"
    Paused = "Paused"
    Running = "Running"
    Cancelled = "Cancelled"
    Completed = "Completed"
    Verified = "Verified"


class WithdrawJob(Base): 
    """
    Model to represent the withdrawal_jobs table.
    """
    __tablename__ = "withdraw_jobs" 

    # Primary Key
    id: Mapped[Optional[int]] = mapped_column(BigInteger, primary_key=True)

    # Foreign Keys
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # CRITICAL FIX: Absolute Foreign Key to PickList
    pick_list_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(PickList.__table__.c.id), 
        nullable=True
    )
    
    # Status (Enum)
    status: Mapped[Optional[str]] = mapped_column(
        SQLEnum(
            WithdrawJobStatus,
            name="withdraw_status",
            nullable=False,
        ),
        default=WithdrawJobStatus.Created,
    )
    
    # Last Transition (datetime)
    last_transition: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    # Run Time
    run_time: Mapped[Optional[timedelta]] = mapped_column(Interval, nullable=False, default=timedelta())
    
    # --- RELATIONSHIPS ---
    
    assigned_user: Mapped[Optional["User"]] = relationship(
        back_populates="withdraw_jobs",
        primaryjoin="WithdrawJob.assigned_user_id==User.id",
        lazy="selectin"
    )

    created_by: Mapped[Optional["User"]] = relationship(
        back_populates="created_withdraw_jobs",
        primaryjoin="WithdrawJob.created_by_id==User.id",
        lazy="selectin"
    )

    # --- RELATIONSHIPS (Many-to-Many via Link Tables) ---
    
    items: Mapped[List["Item"]] = relationship(
        back_populates="withdraw_jobs", 
        secondary=ItemWithdrawalTable, 
        primaryjoin=id == ItemWithdrawalTable.c.withdraw_job_id,
        secondaryjoin="Item.id == item_withdrawals.c.item_id",
    )
    
    non_tray_items: Mapped[List["NonTrayItem"]] = relationship(
        back_populates="withdraw_jobs", 
        secondary=NonTrayItemWithdrawalTable,
        primaryjoin=id == NonTrayItemWithdrawalTable.c.withdraw_job_id,
        secondaryjoin="NonTrayItem.id == non_tray_item_withdrawals.c.non_tray_item_id",
    )
    
    trays: Mapped[List["Tray"]] = relationship(
        back_populates="withdraw_jobs", 
        secondary=TrayWithdrawalTable,
        primaryjoin=id == TrayWithdrawalTable.c.withdraw_job_id,
        secondaryjoin="Tray.id == tray_withdrawals.c.tray_id",
    )
    
    # --- RELATIONSHIPS (Standard) ---
    
    # CRITICAL FIX: Explicit foreign_keys using the column object defined above
    pick_list: Mapped[Optional["PickList"]] = relationship(
        back_populates="withdraw_jobs",
        foreign_keys=[pick_list_id]
    )
    
    batch_upload: Mapped[Optional["BatchUpload"]] = relationship(back_populates="withdraw_job")