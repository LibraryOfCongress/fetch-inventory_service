# /app/models/link_tables.py - FINAL EXPANSION

import sqlalchemy as sa
from sqlalchemy import Table, Column, ForeignKey, BigInteger, Integer, UniqueConstraint, DateTime, func
from app.database.base import Base 

# ... (Previous Withdrawal Tables remain here) ...
# 1. ItemWithdrawal Link Table
ItemWithdrawalTable = Table(
    "item_withdrawals", Base.metadata,
    Column("id", sa.BigInteger, primary_key=True),
    Column("item_id", sa.Integer, ForeignKey("items.id"), nullable=False),
    Column("withdraw_job_id", sa.BigInteger, ForeignKey("withdraw_jobs.id"), nullable=False),
    Column("create_dt", sa.DateTime(timezone=True), default=func.now(), nullable=False),
    Column("update_dt", sa.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False),
    UniqueConstraint("item_id", "withdraw_job_id", name="uix_item_withdrawals")
)

# 2. NonTrayItemWithdrawal Link Table
NonTrayItemWithdrawalTable = Table(
    "non_tray_item_withdrawals", Base.metadata,
    Column("id", sa.BigInteger, primary_key=True),
    Column("non_tray_item_id", sa.Integer, ForeignKey("non_tray_items.id"), nullable=False),
    Column("withdraw_job_id", sa.BigInteger, ForeignKey("withdraw_jobs.id"), nullable=False),
    Column("create_dt", sa.DateTime(timezone=True), default=func.now(), nullable=False),
    Column("update_dt", sa.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False),
    UniqueConstraint("non_tray_item_id", "withdraw_job_id", name="uix_non_tray_item_withdrawals")
)

# 3. TrayWithdrawal Link Table
TrayWithdrawalTable = Table(
    "tray_withdrawals", Base.metadata,
    Column("id", sa.BigInteger, primary_key=True),
    Column("tray_id", sa.Integer, ForeignKey("trays.id"), nullable=False),
    Column("withdraw_job_id", sa.BigInteger, ForeignKey("withdraw_jobs.id"), nullable=False),
    Column("create_dt", sa.DateTime(timezone=True), default=func.now(), nullable=False),
    Column("update_dt", sa.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False),
    UniqueConstraint("tray_id", "withdraw_job_id", name="uix_tray_withdrawals")
)

# --- NEW: Refile Link Tables ---

# 4. RefileItem Link Table
RefileItemTable = Table(
    "refile_items", Base.metadata,
    Column("id", sa.BigInteger, primary_key=True),
    Column("item_id", sa.Integer, ForeignKey("items.id"), nullable=False),
    Column("refile_job_id", sa.SmallInteger, ForeignKey("refile_jobs.id"), nullable=False),
    Column("create_dt", sa.DateTime(timezone=True), default=func.now(), nullable=False),
    Column("update_dt", sa.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False),
    UniqueConstraint("item_id", "refile_job_id", name="uq_item_id_refile_job_id")
)

# 5. RefileNonTrayItem Link Table
RefileNonTrayItemTable = Table(
    "refile_non_tray_items", Base.metadata,
    Column("id", sa.BigInteger, primary_key=True),
    Column("non_tray_item_id", sa.Integer, ForeignKey("non_tray_items.id"), nullable=False),
    Column("refile_job_id", sa.SmallInteger, ForeignKey("refile_jobs.id"), nullable=False),
    Column("create_dt", sa.DateTime(timezone=True), default=func.now(), nullable=False),
    Column("update_dt", sa.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False),
    UniqueConstraint("non_tray_item_id", "refile_job_id", name="uq_non_tray_item_id_refile_job_id")
)