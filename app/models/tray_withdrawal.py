from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa

from sqlmodel import Field, SQLModel


class TrayWithdrawal(SQLModel, table=True):
    """
    Model to represent the tray_withdrawals table.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "tray_withdrawals"
    __table_args__ = (
        sa.UniqueConstraint("tray_id", "withdraw_job_id", name="uix_tray_withdrawals"),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    tray_id: int = Field(default=None, nullable=False, foreign_key="trays.id")
    withdraw_job_id: int = Field(
        default=None, nullable=False, foreign_key="withdraw_jobs.id"
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
