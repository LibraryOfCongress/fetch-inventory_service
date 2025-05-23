import uuid
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import backref
from sqlmodel import SQLModel, Field, Relationship

from app.models.barcodes import Barcode
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.refile_jobs import RefileJob
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.withdraw_jobs import WithdrawJob


class NonTrayItemStatus(str, Enum):
    In = "In"
    Out = "Out"
    Requested = "Requested"
    PickList = "PickList"
    Withdrawn = "Withdrawn"


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
    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
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
        sa_column=sa.Column(
            UUID(as_uuid=True),
            sa.ForeignKey("barcodes.id", name="withdrawn_non_tray_item_barcode_id"),
            unique=True,
            default=None,
            nullable=True
        )
    )
    withdrawn_location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(175), nullable=True, unique=False, default=None)
    )
    withdrawn_internal_location: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(200), nullable=True, unique=False, default=None)
    )
    withdrawn_loc_bcodes: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(150), nullable=True, unique=False, default=None)
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
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    scanned_for_verification: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    scanned_for_shelving: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    scanned_for_refile_queue: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    scanned_for_refile: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=None, nullable=True)
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    shelving_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="shelving_jobs.id"
    )
    shelf_position_id: Optional[int] = Field(
        foreign_key="shelf_positions.id", nullable=True, unique=True
    )
    shelf_position_proposed_id: Optional[int] = Field(
        sa_column=sa.Column(sa.Integer, nullable=True, unique=False)
    )
    accession_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    withdrawal_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    shelved_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    condition: str = Field(
        sa_column=sa.Column(sa.VARCHAR(30), nullable=True, unique=False)
    )
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    scanned_for_refile_queue_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    scanned_for_refile_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    @property
    def last_requested_dt(self):
        if not self.requests:
            return None
        return max(request.create_dt for request in self.requests)

    @property
    def last_refiled_dt(self):
        if not self.refile_jobs:
            return None
        return max(refile_job.update_dt for refile_job in self.refile_jobs)

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
    refile_jobs: List[RefileJob] = Relationship(
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
    non_tray_items_retrieval_events: List["NonTrayItemRetrievalEvent"] = (
        Relationship(
        back_populates="non_tray_item"
    ))
    move_discrepancies: List["MoveDiscrepancy"] = Relationship(
        back_populates="non_tray_item",
        sa_relationship_kwargs={
            "primaryjoin": "MoveDiscrepancy.non_tray_item_id==NonTrayItem.id",
            "lazy": "selectin"
        }
    )
