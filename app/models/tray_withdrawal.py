# /app/models/tray_withdrawal.py - FINAL CIRCULAR IMPORT FIX (REVERTED FOR M2M)

from datetime import datetime, timezone
from typing import Optional 
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from app.database.base import Base
from app.models.withdraw_jobs import WithdrawJob 
from app.models.link_tables import (
    TrayWithdrawalTable
)

class TrayWithdrawal(Base):
    # CRITICAL FIX: Explicitly link the class to the external Table object
    __table__ = TrayWithdrawalTable 

    # Mapped columns are retained for type-checking and property access
    id: Mapped[Optional[int]]
    tray_id: Mapped[int]
    withdraw_job_id: Mapped[int]