import uuid
import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import backref
from sqlmodel import SQLModel, Field, Relationship

from app.models.barcodes import Barcode
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.refile_jobs import RefileJob
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.withdraw_jobs import WithdrawJob


class NonTrayItemStatus(str, Enum):
    In = "In"
    Requested = "Requested"
    Withdrawn = "Withdrawn"
    Out = "Out"


class NonTrayItem(SQLModel, table=True):
    """
    Model to represent the non_tray_items table.
        Non tray items have a barcode, and while they may be a container,
        we view these as a standalone entity and ignore their contents.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "non_tray_items"
    __table_args__ = (
        sa.CheckConstraint(
            "(barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)",
            name="ck_non_tray_item_barcode_xor_withdrawn_barcode",
        ),
    )
    id: Optional[int] = Field(primary_key=True, sa_column=sa.BigInteger, default=None)
    status: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                NonTrayItemStatus,
                name="non_tray_item_status",
                nullable=False,
            )
        ),
        default=NonTrayItemStatus.In,
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=True, default=None, unique=True
    )
    withdrawn_barcode_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("barcodes.id", name="withdrawn_non_tray_item_barcode_id"),
            unique=True
        )
    )
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    size_class_id: Optional[int] = Field(foreign_key="size_class.id", nullable=True)
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    subcollection_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="subcollections.id"
    )
    accession_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="accession_jobs.id"
    )
    scanned_for_accession: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    scanned_for_verification: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    scanned_for_shelving: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    scanned_for_refile_queue: Optional[bool] = Field(
        sa_column=sa.Boolean, default=False, nullable=False
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    shelving_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="shelving_jobs.id"
    )
    shelf_position_id: Optional[int] = Field(
        foreign_key="shelf_positions.id", nullable=True
    )
    shelf_position_proposed_id: Optional[int] = Field(
        sa_column=sa.Column(sa.Integer, nullable=True, unique=False)
    )
    accession_dt: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
    withdrawal_dt: Optional[datetime] = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
    condition: str = Field(
        max_length=30, sa_column=sa.VARCHAR, nullable=True, unique=False
    )
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    scanned_for_refile_queue_dt: datetime = Field(
        sa_column=sa.DateTime, default=None, nullable=True
    )
    create_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    update_dt: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow), nullable=False
    )
    barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs=dict(
            backref=backref("barcode_non_tray_item"),
            foreign_keys="NonTrayItem.barcode_id",
            uselist=False
        )
    )
    withdrawn_barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs=dict(
            backref=backref("withdrawn_non_tray_item"),
            foreign_keys="NonTrayItem.withdrawn_barcode_id",
            uselist=False
        )
    )
    media_type: Optional["MediaType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    size_class: Optional["SizeClass"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    container_type: Optional["ContainerType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    owner: Optional["Owner"] = Relationship(sa_relationship_kwargs={"uselist": False})
    accession_job: Optional["AccessionJob"] = Relationship(
        back_populates="non_tray_items"
    )
    verification_job: Optional["VerificationJob"] = Relationship(
        back_populates="non_tray_items"
    )
    shelving_job: Optional["ShelvingJob"] = Relationship(
        back_populates="non_tray_items"
    )
    shelf_position: Optional["ShelfPosition"] = Relationship(
        back_populates="non_tray_item"
    )
    subcollection: Optional["Subcollection"] = Relationship(
        back_populates="non_tray_items"
    )
    refile_jobs: Optional[RefileJob] = Relationship(
        back_populates="non_tray_items", link_model=RefileNonTrayItem
    )
    requests: List["Request"] = Relationship(back_populates="non_tray_item")
    withdraw_jobs: List[WithdrawJob] = Relationship(
        back_populates="non_tray_items", link_model=NonTrayItemWithdrawal
    )
    shelving_job_discrepancies: List["ShelvingJobDiscrepancy"] = Relationship(
        back_populates="non_tray_item",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJobDiscrepancy.non_tray_item_id==NonTrayItem.id",
            "lazy": "selectin"
        }
    )
