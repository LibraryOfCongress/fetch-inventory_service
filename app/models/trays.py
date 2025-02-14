import uuid
import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import backref
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import SQLModel, Field, Relationship

from app.models.barcodes import Barcode
from app.models.items import Item
from app.models.tray_withdrawal import TrayWithdrawal
from app.models.withdraw_jobs import WithdrawJob


class Tray(SQLModel, table=True):
    """
    Model to represent the trays table.
        Trays can be assigned to shelf positions and contains Items.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "trays"
    __table_args__ = (
        sa.CheckConstraint(
            "(barcode_id IS NOT NULL) OR (withdrawn_barcode_id IS NOT NULL)",
            name="ck_tray_barcode_xor_withdrawn_barcode",
        ),
    )

    id: Optional[int] = Field(sa_column=sa.Column(sa.BigInteger, primary_key=True), default=None)
    accession_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="accession_jobs.id"
    )
    verification_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="verification_jobs.id"
    )
    shelving_job_id: Optional[int] = Field(
        default=None, nullable=True, foreign_key="shelving_jobs.id"
    )
    container_type_id: Optional[int] = Field(
        foreign_key="container_types.id", nullable=True
    )
    barcode_id: uuid.UUID = Field(
        foreign_key="barcodes.id", nullable=True, default=None, unique=True
    )
    withdrawn_barcode_id: Optional[uuid.UUID] = Field(
        sa_column=sa.Column(
            UUID(as_uuid=True),
            ForeignKey("barcodes.id", name="withdrawn_tray_barcode_id"),
            unique=True,
            default=None,
            nullable=True,
        )
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
    collection_accessioned: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    collection_verified: Optional[bool] = Field(
        sa_column=sa.Column(sa.Boolean, default=False, nullable=False)
    )
    size_class_id: int = Field(foreign_key="size_class.id", nullable=False)
    owner_id: Optional[int] = Field(foreign_key="owners.id", nullable=True)
    media_type_id: Optional[int] = Field(foreign_key="media_types.id", nullable=True)
    shelf_position_id: Optional[int] = Field(
        foreign_key="shelf_positions.id", nullable=True
    )
    shelf_position_proposed_id: Optional[int] = Field(
        sa_column=sa.Column(sa.Integer, nullable=True, unique=False)
    )
    conveyance_bin_id: Optional[int] = Field(
        foreign_key="conveyance_bins.id", nullable=True
    )
    accession_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    shelved_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    withdrawal_dt: Optional[datetime] = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=None, nullable=True)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # derived item count
    # derived item out count

    barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs=dict(
            backref=backref("barcode_tray"),
            foreign_keys="Tray.barcode_id",
            uselist=False
        )
    )
    withdrawn_barcode: Optional["Barcode"] = Relationship(
        sa_relationship_kwargs=dict(
            backref=backref("withdrawn_tray"),
            foreign_keys="Tray.withdrawn_barcode_id",
            uselist=False
        )
    )
    media_type: Optional["MediaType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    owner: Optional["Owner"] = Relationship(sa_relationship_kwargs={"uselist": False})
    container_type: Optional["ContainerType"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    size_class: Optional["SizeClass"] = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    shelf_position: Optional["ShelfPosition"] = Relationship(back_populates="tray")
    conveyance_bin: Optional["ConveyanceBin"] = Relationship(back_populates="trays")
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="trays")
    verification_job: Optional["VerificationJob"] = Relationship(back_populates="trays")
    shelving_job: Optional["ShelvingJob"] = Relationship(back_populates="trays")
    items: List[Item] = Relationship(back_populates="tray")
    withdraw_jobs: List[WithdrawJob] = Relationship(
        back_populates="trays", link_model=TrayWithdrawal
    )
    shelving_job_discrepancies: List["ShelvingJobDiscrepancy"] = Relationship(
        back_populates="tray",
        sa_relationship_kwargs={
            "primaryjoin": "ShelvingJobDiscrepancy.tray_id==Tray.id",
            "lazy": "selectin"
        }
    )
