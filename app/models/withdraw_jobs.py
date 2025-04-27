from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
import sqlalchemy as sa
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field, Relationship

from app.models.item_withdrawals import ItemWithdrawal
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.pick_lists import PickList


class WithdrawJobStatus(str, Enum):
    Created = "Created"
    Paused = "Paused"
    Running = "Running"
    Cancelled = "Cancelled"
    Completed = "Completed"
    Verified = "Verified"


class WithdrawJob(SQLModel, table=True):
    """
    Model to represent the withdrawal_jobs table.
        Withdrawal Jobs can be assigned to trays and contain Items.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "withdraw_jobs"

    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    assigned_user_id: Optional[int] = Field(
        foreign_key="users.id", nullable=True, unique=False
    )
    created_by_id: Optional[int] = Field(foreign_key="users.id", nullable=True)
    status: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                WithdrawJobStatus,
                name="withdraw_status",
                nullable=False,
            )
        ),
        default=WithdrawJobStatus.Created,
    )
    last_transition: Optional[datetime] = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    run_time: Optional[timedelta] = Field(
        sa_column=sa.Interval(6), nullable=False, default=timedelta()
    )
    pick_list_id: Optional[int] = Field(foreign_key="pick_lists.id", nullable=True)
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )

    assigned_user: Optional["User"] = Relationship(
        back_populates="withdraw_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "WithdrawJob.assigned_user_id==User.id",
            "lazy": "selectin"
        }
    )

    created_by: Optional["User"] = Relationship(
        back_populates="created_withdraw_jobs",
        sa_relationship_kwargs={
            "primaryjoin": "WithdrawJob.created_by_id==User.id",
            "lazy": "selectin"
        }
    )

    items: List["Item"] = Relationship(
        back_populates="withdraw_jobs", link_model=ItemWithdrawal
    )
    non_tray_items: List["NonTrayItem"] = Relationship(
        back_populates="withdraw_jobs", link_model=NonTrayItemWithdrawal
    )
    trays: List["Tray"] = Relationship(
        back_populates="withdraw_jobs", link_model=TrayWithdrawal
    )
    pick_list: Optional["PickList"] = Relationship(back_populates="withdraw_jobs")
    batch_upload: Optional["BatchUpload"] = Relationship(back_populates="withdraw_job")
