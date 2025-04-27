from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa

from sqlmodel import Field, SQLModel


class NonTrayItemWithdrawal(SQLModel, table=True):
    """
    Model to represent the non_tray_item_withdrawals table.
        Non Tray Item withdrawals have a barcode, and while they may be a container,
        we view these as a standalone entity and ignore their contents.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "non_tray_item_withdrawals"
    __table_args__ = (
        sa.UniqueConstraint(
            "non_tray_item_id", "withdraw_job_id", name="uix_non_tray_item_withdrawals"
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    non_tray_item_id: int = Field(
        default=None, nullable=False, foreign_key="non_tray_items.id"
    )
    withdraw_job_id: int = Field(
        default=None, nullable=False, foreign_key="withdraw_jobs.id"
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
