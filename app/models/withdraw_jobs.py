from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Relationship

from app.models.item_withdrawals import ItemWithdrawal
from app.models.non_tray_items import NonTrayItem
from app.models.tray_withdrawal import TrayWithdrawal


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
    status: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                WithdrawJobStatus,
                name="withdraw_job_status",
                nullable=False,
            )
        ),
        default=WithdrawJobStatus.Created,
    )
    last_transition: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=True
    )
    run_time: Optional[timedelta] = Field(
        sa_column=sa.Interval(6), nullable=False, default=timedelta()
    )
    pick_list_id: Optional[int] = Field(foreign_key="pick_lists.id", nullable=True)
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    items: Optional[list["Item"]] = Relationship(
        back_populates="withdraw_jobs", link_model=ItemWithdrawal
    )
    trays: Optional[list["Tray"]] = Relationship(
        back_populates="withdraw_jobs", link_model=TrayWithdrawal
    )
    non_tray_items: Optional[list["NonTrayItem"]] = Relationship(
        back_populates="withdraw_jobs", link_model=NonTrayItem
    )
