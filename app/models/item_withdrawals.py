# /app/models/item_withdrawals.py - FINAL CORRECTED V2

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlalchemy.schema import UniqueConstraint

from app.database.base import Base
from app.models.withdraw_jobs import WithdrawJob 
from app.models.link_tables import ItemWithdrawalTable # CRITICAL IMPORT

if TYPE_CHECKING:
    from app.models.items import Item


class ItemWithdrawal(Base): 
    # CRITICAL FIX: Explicitly link the class to the external Table object
    __table__ = ItemWithdrawalTable 

    # NOTE: These Mapped columns are retained for ORM type-checking and property access
    id: Mapped[Optional[int]]
    item_id: Mapped[int]
    withdraw_job_id: Mapped[int]