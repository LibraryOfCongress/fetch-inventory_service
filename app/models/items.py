import uuid
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import backref

from app.models.barcodes import Barcode
from app.models.refile_items import RefileItem
from app.models.refile_jobs import RefileJob
from app.models.item_withdrawals import ItemWithdrawal
from app.models.withdraw_jobs import WithdrawJob


class ItemStatus(str, Enum):
    In = "In"
    Out = "Out"
    Requested = "Requested"
    PickList = "PickList"
    Withdrawn = "Withdrawn"


class Item(SQLModel, table=True):
    """
    Model to represent the Items table.
        Items can be assigned to Trays, and each have a barcode.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "items"
    __table_args__ = (
        sa.CheckConstraint(
            "(barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)",
            name="ck_items_barcode_xor_withdrawn_barcode",
        ),
    )
    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    status: Optional[str] = Field(
        sa_column=sa.Column(
            sa.Enum(
                ItemStatus,
                name="item_status",
                nullable=False,
            )
        ),
        default=ItemStatus.In,
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=True, default=None, unique=True
    )
    withdrawn_barcode_id: Optional[uuid.UUID] = Field(
        sa_column=sa.Column(
            UUID(as_uuid=True),
            sa.ForeignKey("barcodes.id", name="withdrawn_item_barcode_id"),
            unique=True,
            default=None,
            nullable=True,
        ),
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
    size_class_id: int = Field(foreign_key="size_class.id", nullable=True)
    tray_id: Optional[int] = Field(default=None, nullable=True, foreign_key="trays.id")
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    title: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(4000), nullable=True, unique=False)
    )
    volume: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(15), nullable=True, unique=False)
    )
    condition: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(30), nullable=True, unique=False)
    )
    arbitrary_data: Optional[str] = Field(
        sa_column=sa.Column(sa.VARCHAR(255), nullable=True, unique=False)
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
    scanned_for_refile_queue: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    accession_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    withdrawal_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    scanned_for_refile_queue_dt: Optional[datetime] = Field(
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
            backref=backref("barcode_item"),
            foreign_keys="Item.barcode_id",
            uselist=False,
        )
    )
    withdrawn_barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs=dict(
            backref=backref("withdrawn_item"),
            foreign_keys="Item.withdrawn_barcode_id",
            uselist=False,
        )
    )
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="items")
    verification_job: Optional["VerificationJob"] = Relationship(back_populates="items")
    subcollection: Optional["Subcollection"] = Relationship(back_populates="items")
    tray: Optional["Tray"] = Relationship(back_populates="items")
    media_type: Optional["MediaType"] = Relationship(back_populates="items")
    size_class: Optional["SizeClass"] = Relationship(back_populates="items")
    container_type: Optional["ContainerType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    owner: Optional["Owner"] = Relationship(back_populates="items")
    refile_jobs: List[RefileJob] = Relationship(
        back_populates="items", link_model=RefileItem
    )
    requests: List["Request"] = Relationship(back_populates="item")
    withdraw_jobs: List[WithdrawJob] = Relationship(
        back_populates="items", link_model=ItemWithdrawal
    )
    items_retrieval_events: List["ItemRetrievalEvent"] = Relationship(
        back_populates="item"
    )
